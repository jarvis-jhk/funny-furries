"""Local-only integration checks for the detached native error courier."""
import http.server
import json
import os
import queue
import subprocess
import sys
import threading
import time

reports = queue.Queue()


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        reports.put(json.loads(self.rfile.read(int(self.headers['content-length']))))
        time.sleep(1)
        self.send_response(204)
        self.end_headers()

    def log_message(self, *_):
        pass


server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/not-a-public-endpoint'
env = dict(os.environ, FF_FAULT_REPORT_URL=url, SDL_VIDEODRIVER='invalid-test-driver')
start = time.monotonic()
r = subprocess.run([sys.argv[1]], env=env, capture_output=True, timeout=3)
assert r.returncode == 1, r.stderr
assert time.monotonic() - start < 1, 'game waited for HTTP response'
report = reports.get(timeout=3)
assert report['lane'] == 'furries' and report['kind'] == 'bug'
assert report['detail'] == 'native-runtime-fault'
assert url not in str(report) and 'invalid-test-driver' not in str(report)
r = subprocess.run([sys.argv[2]], env=env, capture_output=True, timeout=3)
assert r.returncode == 128 + 6, r.returncode
assert reports.get(timeout=3)['detail'] == 'native-process-signal'
# Invalid command line is a user error, never a crash report.
r = subprocess.run([sys.argv[1], '--invalid'], env=env, capture_output=True, timeout=3)
assert r.returncode == 2 and reports.empty()
server.shutdown()
print('runtime, crash, privacy and nonblocking fault checks passed')
