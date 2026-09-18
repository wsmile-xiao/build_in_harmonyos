#!/usr/bin/env python3
"""Consumer test for the packaged kea-shell 3.0.3.

Runs the packaged command-line tool (found through the Conan run environment)
and checks the version output plus real HTTP round trips against a stub Kea
control endpoint.  The round trips are what prove the two helper modules
kea_conn / kea_connector3 are installed where the script can import them.
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EXPECTED_BODY = {"command": "list-commands", "service": ["dhcp4"]}
failures = []
checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        failures.append(message)


SHELL = shutil.which("kea-shell")
if not SHELL:
    print("kea-shell is not on PATH - the package exposes no runnable command")
    sys.exit(1)
print("kea-shell:", SHELL)


class StubKea(BaseHTTPRequestHandler):
    """Echoes back what kea-shell sent, in the shape of a Kea response."""

    def do_POST(self):  # noqa: N802 (http.server API)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        payload = json.dumps({
            "result": 0,
            "text": "commands returned",
            "received": json.loads(body),
            "request-line": f"{self.command} {self.path}",
            "user-agent": self.headers.get("User-Agent"),
            "content-type": self.headers.get("Content-Type"),
            "content-length": self.headers.get("Content-Length"),
            "authorization": self.headers.get("Authorization"),
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def run(*args, **kwargs):
    # kea-shell reads its optional extra arguments from stdin until EOF
    # ("for line in sys.stdin", kea-shell.in).  Without an explicit EOF the
    # command blocks forever whenever the caller's stdin stays open - which is
    # exactly what happens on the CI worker, whose stdin is a never-closing
    # pipe (upstream's own tests therefore always feed it, e.g. `echo | kea-shell`).
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    return subprocess.run([SHELL, *args], capture_output=True, text=True,
                          timeout=30, **kwargs)


# --- version output -----------------------------------------------------------
version = run("-v")
check(version.returncode == 0, f"-v exited with {version.returncode}")
check(version.stdout.strip() == "3.0.3",
      f"-v printed {version.stdout.strip()!r}, expected '3.0.3'")

extended = run("-V")
check(extended.returncode == 0, f"-V exited with {extended.returncode}")
check(extended.stdout.strip().startswith("3.0.3"),
      f"-V printed {extended.stdout.strip()!r}, expected the 3.0.3 extended version")

# --- half-configured TLS must be rejected before any connection ---------------
half_tls = run("--cert", "/nonexistent/cert.pem", "list-commands")
check(half_tls.returncode == 1,
      f"--cert without --key exited with {half_tls.returncode}, expected 1")
check("--cert and --key must be used together" in half_tls.stdout,
      "the --cert/--key guard message is missing")

# --- real HTTP round trips ----------------------------------------------------
server = ThreadingHTTPServer(("127.0.0.1", 0), StubKea)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    plain = run("--host", "127.0.0.1", "--port", str(port),
                "--service", "dhcp4", "list-commands")
    auth = run("--host", "127.0.0.1", "--port", str(port),
               "--service", "dhcp4", "--auth-user", "admin",
               "--auth-password", "secret", "list-commands")
finally:
    server.shutdown()
    server.server_close()

check(plain.returncode == 0,
      f"the HTTP round trip exited with {plain.returncode}: "
      f"{plain.stdout.strip()} {plain.stderr.strip()}")
try:
    payload = json.loads(plain.stdout)
except ValueError:
    check(False, f"the response is not JSON: {plain.stdout.strip()!r}")
else:
    check(payload.get("received") == EXPECTED_BODY,
          f"kea-shell sent {payload.get('received')!r}, expected {EXPECTED_BODY!r}")
    check(str(payload.get("user-agent", "")).startswith("Kea-shell/3.0.3"),
          f"unexpected User-Agent {payload.get('user-agent')!r}")
    check(payload.get("content-type") == "application/json",
          f"unexpected Content-Type {payload.get('content-type')!r}")

expected_auth = "Basic " + base64.b64encode(b"admin:secret").decode("ascii")
try:
    auth_payload = json.loads(auth.stdout)
except ValueError:
    check(False, f"the authenticated response is not JSON: {auth.stdout.strip()!r}")
else:
    check(auth_payload.get("authorization") == expected_auth,
          f"unexpected Authorization header {auth_payload.get('authorization')!r}")

# --- unreachable endpoint must fail cleanly ----------------------------------
dead = run("--host", "127.0.0.1", "--port", str(port), "--timeout", "3",
           "list-commands")
check(dead.returncode == 1,
      f"an unreachable endpoint exited with {dead.returncode}, expected 1")

# --- HarmonyOS-specific case: the OHOS adaptations in the packaged artefact ---
# kea-shell needs two OHOS portability adaptations to be usable on a HarmonyOS
# device; both are visible in the packaged files, so assert them from outside:
#   * patches/0002 replaces the shebang with `/usr/bin/env python3`, because
#     upstream writes the build machine's absolute interpreter path into the
#     script (a path under the builder's home directory, absent on the target);
#   * the two helper modules are installed next to the script, because
#     upstream's PKGPYTHONDIR points at the build host's `purelib/kea`, which a
#     Conan package cannot own.
shell_dir, shell_name = os.path.split(os.path.realpath(SHELL))
with open(SHELL, encoding="utf-8", errors="replace") as handle:
    shebang = handle.readline().rstrip("\n")
check(shebang == "#!/usr/bin/env python3",
      f"the OHOS shebang patch is not in effect: first line is {shebang!r}")
check(os.path.exists("/usr/bin/env"),
      "/usr/bin/env is missing, so the env-form shebang cannot be honoured "
      "(OHOS provides it through toybox - see knowledge E037)")
for module in ("kea_conn.py", "kea_connector3.py"):
    check(os.path.isfile(os.path.join(shell_dir, module)),
          f"{module} is not installed next to {shell_name}")

print(f"checks run: {checks}")
if failures:
    for failure in failures:
        print("FAIL:", failure)
    sys.exit(1)
print("all checks passed")
