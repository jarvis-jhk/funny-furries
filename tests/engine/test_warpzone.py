"""Online play over Warpzone between real game processes and a real local server.

usage: test_warpzone.py GAME SERVER RELAY_ONLY_SO

Rooms: a 2 vs 2 with two players per machine on a bad line, joined by room
code, directly and once more with every direct datagram dropped so the relay
has to carry it. Ranked: 1 vs 1, four-player free-for-all and 2 vs 2 through
the queues; every machine must report the same placements and final-state hash
and the server must rate the match.
"""
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

GAME, SERVER, RELAY_ONLY = sys.argv[1:4] if len(sys.argv) >= 4 else (None, None, None)
DESCRIPTOR = '''id = "funny-furries"
name = "Funny Furries"
tagline = "Test descriptor."
tier = 3
[install]
github = "jarvis-jhk/funny-furries"
assets = { linux = "funny-furries-linux-deck-x86_64.tar.gz", windows = "funny-furries-windows-x86_64.zip" }
[launch]
exec = { linux = "funny-furries/play.sh", windows = "funny-furries/Play-Funny-Furries.exe" }
join = ["--warpzone-join", "{room}"]
host = ["--warpzone-host"]
[rooms]
max_players = 4
presets = [{ id = "1v1", label = "1 vs 1" }, { id = "ffa", label = "free-for-all" }, { id = "2v2", label = "2 vs 2" }]
display = [{ key = "arena", label = "Arena" }, { key = "mode", label = "Mode" }]
[[ladder]]
id = "1v1"
title = "1 vs 1"
teams = 2
[[ladder]]
id = "ffa"
title = "Free-for-all (4)"
teams = 4
[[ladder]]
id = "2v2"
title = "2 vs 2"
teams = 2
team_size = 2
'''


class Warpzone(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        root = cls.dir.name
        os.makedirs(os.path.join(root, 'games'))
        with open(os.path.join(root, 'games', 'funny-furries.toml'), 'w') as f:
            f.write(DESCRIPTOR)
        open(os.path.join(root, 'staff.toml'), 'w').write('moderators = []\nreviewers = []\n')
        with open(os.path.join(root, 'server.toml'), 'w') as f:
            f.write('name = "test"\npublic_url = "http://127.0.0.1:2999"\nhttp_listen = "127.0.0.1:2999"\n'
                    'udp_listen = "127.0.0.1:3479"\ndata_dir = "data"\ngames_dir = "games"\nstaff_file = "staff.toml"\n')
        cls.log = open(os.path.join(root, 'server.log'), 'w')
        cls.server = subprocess.Popen([SERVER, '--config', 'server.toml'], cwd=root, stdout=cls.log, stderr=subprocess.STDOUT)
        for _ in range(100):
            try:
                urllib.request.urlopen('http://127.0.0.1:2999/api/v1/info', timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        cls.homes = [os.path.join(root, 'home%d' % i) for i in range(4)]

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.wait()
        cls.log.close()
        cls.dir.cleanup()

    def env(self, n, **extra):
        e = dict(os.environ, WARPZONE_SERVER='http://127.0.0.1:2999', WARPZONE_HOME=self.homes[n],
                 FF_WZ_NAME='Tester%d' % n, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', FF_NO_REPORT='1')
        e.update(extra)
        return e

    def finish(self, procs):
        outs = []
        for p in procs:
            out, _ = p.communicate(timeout=240)
            outs.append(out)
            self.assertEqual(p.returncode, 0, out[-3000:])
        return outs

    def room_match(self, relay):
        extra = {'LD_PRELOAD': RELAY_ONLY, 'RELAY_ONLY_PORT': '3479'} if relay else {}
        host = subprocess.Popen([GAME, '--warpzone-host', '--local', '2', '--smoke', '1500', '--players', '4', '--teams'],
                                env=self.env(0, FF_WZ_VERBOSE='1', **extra), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        code = None
        lines = []
        deadline = time.time() + 60
        while code is None and time.time() < deadline:
            line = host.stdout.readline()
            lines.append(line)
            m = re.match(r'warpzone code=([A-Z0-9]{6})', line)
            if m:
                code = m.group(1)
        self.assertIsNotNone(code, ''.join(lines)[-3000:])
        guest = subprocess.Popen([GAME, '--warpzone-code', code, '--local', '2', '--smoke', '1500'],
                                 env=self.env(1, FF_WZ_VERBOSE='1', FF_NET_LOSS='10', FF_NET_DELAY='40', FF_NET_JITTER='30', **extra),
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        host_out, guest_out = self.finish([host, guest])
        host.stdout.close()
        guest.stdout.close()
        host_out = ''.join(lines) + host_out
        states = [re.findall(r'^online frame=(\d+) state=(\w+)', o, re.M) for o in (host_out, guest_out)]
        self.assertTrue(states[0], host_out[-3000:])
        self.assertEqual(states[0], states[1])
        path = '"relayed":true' if relay else '"relayed":false'
        self.assertIn(path, host_out)
        self.assertIn(path, guest_out)
        return states[0]

    def test_1_room_direct(self):
        self.room_match(relay=False)

    def test_2_room_relayed(self):
        self.room_match(relay=True)

    def ranked(self, queue, players):
        procs = [subprocess.Popen([GAME, '--ranked', queue, '--smoke', '1'], env=self.env(n, FF_RANKED_WINS='1', FF_WZ_VERBOSE='1'),
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) for n in range(players)]
        outs = self.finish(procs)
        results = [re.findall(r'^ranked match=(\w+) frame=(\d+) state=(\w+) result=(\w+)', o, re.M) for o in outs]
        reports = [re.findall(r'^warpzone report match=\w+ (.*)$', o, re.M) for o in outs]
        for o, r in zip(outs, results):
            self.assertEqual(len(r), 1, o[-3000:])
            self.assertEqual(r[0][3], 'RATED')
        self.assertEqual(len({r[0] for r in results}), 1)
        self.assertEqual(len({rep[0] for rep in reports}), 1)
        print(queue, results[0][0], reports[0][0])

    def test_3_ranked_1v1(self):
        self.ranked('1v1', 2)

    def test_4_ranked_ffa(self):
        self.ranked('ffa', 4)

    def test_5_ranked_2v2(self):
        self.ranked('2v2', 4)


if __name__ == '__main__':
    unittest.main(argv=sys.argv[:1], verbosity=2)
