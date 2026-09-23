#!/bin/sh
# redir 3.3 consumer validation:
#  1) CLI smoke: `redir -h` must exit 0
#  2) E2E TCP redirect: echo server <- redir tunnel <- client
#     (uses only the installed public binary; -n keeps redir in foreground)
set -eu

REDIR_BIN="$1"

echo "== [1/2] CLI smoke: $REDIR_BIN -h"
"$REDIR_BIN" -h >/dev/null 2>&1 || {
    echo "FAIL: redir -h exited non-zero" >&2
    exit 1
}
echo "OK: redir -h"

echo "== [2/2] E2E TCP redirect (consumer)"
python3 - "$REDIR_BIN" <<'PYEOF'
import socket
import subprocess
import sys
import threading
import time

redir_bin = sys.argv[1]

# 1) local echo listener (the "upstream service")
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 0))
srv.listen(1)
srv_port = srv.getsockname()[1]

def echo():
    conn, _ = srv.accept()
    data = conn.recv(4096)
    conn.sendall(data)
    conn.close()

t = threading.Thread(target=echo)
t.daemon = True
t.start()

# 2) free source port for redir to listen on
probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
probe.bind(("127.0.0.1", 0))
src_port = probe.getsockname()[1]
probe.close()

# 3) run installed redir in foreground: SRC:PORT -> 127.0.0.1:SRV_PORT
#    (upstream arg syntax requires the `:` in [SRC]:PORT)
proc = subprocess.Popen(
    [redir_bin, "-n", "127.0.0.1:%d" % src_port, "127.0.0.1:%d" % srv_port],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
try:
    # wait for listener
    deadline = time.time() + 10
    while True:
        try:
            sock = socket.create_connection(("127.0.0.1", src_port), timeout=2)
            break
        except OSError:
            if time.time() > deadline:
                out, err = proc.communicate(timeout=2)
                raise RuntimeError("redir listener never came up: "
                                   + err.decode())
            time.sleep(0.2)

    # 4) push payload through the tunnel and assert echo
    payload = b"redir-consumer-e2e-payload"
    sock.sendall(payload)
    echo_back = sock.recv(4096)
    sock.close()
    if echo_back != payload:
        raise RuntimeError("echo mismatch: got %r" % echo_back)
    print("OK: E2E TCP redirect round-trip matched (%d bytes)" % len(payload))
finally:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    t.join(timeout=2)
PYEOF
echo "ALL TESTS PASSED"