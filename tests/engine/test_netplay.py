#!/usr/bin/env python3
"""Real processes over loopback UDP under simulated loss and latency must agree
on the checksum of a confirmed frame, and that checksum must equal an offline
run of the same controls."""
import os
import re
import subprocess
import sys
import time

PROBE = sys.argv[1]


def run(cases):
    for seats, mode, frames, guests, line, port in cases:
        env = dict(os.environ, FF_PROBE_MS='10', **line)
        host = subprocess.Popen([PROBE, 'host', str(port), str(seats), mode, str(frames), str(guests[0])],
                                stdout=subprocess.PIPE, text=True, env=env)
        host.stdout.readline()
        joiners = []
        for local in guests[1:]:
            # Join codes are covered by test_net; loopback needs the plain address form.
            joiners.append(subprocess.Popen([PROBE, 'join', '127.0.0.1:%d' % port, str(frames), str(local)],
                                            stdout=subprocess.PIPE, text=True, env=env))
            time.sleep(0.2)
        outputs = []
        for process in [host] + joiners:
            out, _ = process.communicate(timeout=150)
            if process.returncode:
                raise SystemExit('probe failed: %r' % out)
            outputs.append(out.strip().splitlines()[-1])
        hashes = {re.search(r'hash=(\w+)', o).group(1) for o in outputs}
        offline = subprocess.run([PROBE, 'offline', str(seats), mode, str(frames - frames % 32)],
                                 capture_output=True, text=True, check=True).stdout
        reference = re.search(r'hash=(\w+)', offline).group(1)
        print(seats, mode, line, outputs, 'offline', reference)
        if hashes != {reference}:
            raise SystemExit('desync: %s vs offline %s' % (hashes, reference))
        if line and not any(int(re.search(r'rollbacks=(\d+)', o).group(1)) for o in outputs):
            raise SystemExit('a bad line should have caused rollbacks')


base = 27600 + os.getpid() % 300
run([
    (2, 'ffa', 480, [1, 1], {}, base),
    (2, 'ffa', 640, [1, 1], {'FF_NET_LOSS': '20', 'FF_NET_DELAY': '40', 'FF_NET_JITTER': '40'}, base + 1),
    (4, 'teams', 640, [1, 1, 2], {'FF_NET_LOSS': '15', 'FF_NET_DELAY': '30', 'FF_NET_JITTER': '50'}, base + 2),
    (4, 'ffa', 640, [1, 1, 1, 1], {'FF_NET_LOSS': '10', 'FF_NET_DELAY': '20', 'FF_NET_JITTER': '30'}, base + 3),
])
print('netplay ok')
