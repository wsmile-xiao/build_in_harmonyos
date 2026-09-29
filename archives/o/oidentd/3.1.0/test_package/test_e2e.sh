#!/bin/sh
# Complete consumer end-to-end suite for the packaged oidentd (RFC 1413):
# two real inetd/stdio consumer sessions are driven end to end. A connected
# socket is handed to `oidentd -I` - exactly how inetd/xinetd hands it over -
# a RFC 1413 query is written to it and the daemon's reply is parsed. Case 2
# uses an out-of-range port pair and must be answered by an ERROR reply.
# usage: sh test_e2e.sh <path to bin/oidentd> [python3]
set -u
BIN=${1:?usage: sh test_e2e.sh <path to bin/oidentd> [python3]}
exec "${2:-python3}" - "$BIN" <<'PYEOF'
import re, socket, subprocess, sys

Q = re.compile(r"^(\d+)\s*,\s*(\d+)\s*:\s*(USERID|ERROR)\s*:\s*(\S.*)$")


def session(query):
    a, b = socket.socketpair()
    p = subprocess.Popen([sys.argv[1], "-I", "-S", "-R", "ident-e2e"], stdin=b, stdout=b)
    b.close()
    a.settimeout(15)
    a.sendall(query)
    o = a.recv(512).decode("utf-8", "replace")
    p.wait(timeout=15)
    a.close()
    return p.returncode, o.strip()

rc, o = session(b"1234,5678"\r\n")
m = Q.match(o)
ok1 = rc == 0 and m is not None and m.group(1) == "1234" and m.group(2) == "5678"
ok1 = ok1 and "ident-e2e" in o
print("PASS" if ok1 else "FAIL", "case 1 consumer session (USERID):", repr(o[:70]))

rc2, o2 = session(b"70000,80\r\n")
m2 = Q.match(o2)
ok2 = rc2 == 0 and m2 is not None and m2.group(3) == "ERROR" and "INVALID-PORT" in o2
print("PASS" if ok2 else "FAIL", "case 2 consumer session (ERROR):", repr(o2[:70]))
print("2 end-to-end consumer cases, 2 assertions,", 0 if ok1 and ok2 else 1, "failed")
sys.exit(0 if ok1 and ok2 else 1)
PYEOF