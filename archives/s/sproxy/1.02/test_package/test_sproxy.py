#!/usr/bin/env python3
"""Consumer test for sproxy 1.02 (usage: test_sproxy.py <package-folder> <work-dir>).

Full consumer flow against the installed package:
  1. `sproxy -V` / `-h` print the substituted version banner / usage;
  2. the installed bin/sproxy (default etc/sproxy.conf, bundled
     lib/sproxy/JoeDog/Config.pm) is started on a free loopback port;
  3. a GET and a POST are sent *through* the proxy to a local origin server;
  4. the forwarded responses must equal the origin's answers, the origin must
     have seen both requests, and sproxy's output file must contain the
     siege-style URL lines (`<url>` and `<url> POST a=1&b=2`);
  5. a text/html response is forwarded while HTML/*.pm is made unloadable
     (the perl dependency ships no HTML::Parser; parse_head must be off).
The package is self-contained (LWP, HTTP::*, URI, JoeDog::Config under
lib/sproxy); the perl used is the first candidate able to run it from there.
"""
import http.client
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PKG, WORK = sys.argv[1], sys.argv[2]
SPROXY = os.path.join(PKG, "bin", "sproxy")
LIBDIR = os.path.join(PKG, "lib", "sproxy")
os.makedirs(WORK, exist_ok=True)

# proxies from the environment would make LWP forward through them
for k in list(os.environ):
    if k.lower() in ("http_proxy", "https_proxy", "all_proxy", "no_proxy"):
        del os.environ[k]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)
    print("  OK:", msg)


# ---- pick a perl that can load the modules sproxy needs -------------------
with open(SPROXY, encoding="utf-8") as fh:
    shebang = fh.readline().strip()
candidates = []
if shebang.startswith("#!"):
    candidates.append(shebang[2:].strip())
candidates += [os.environ.get("PERL"), shutil.which("perl"),
               "/data/service/hnp/bin/perl",
               "/storage/Users/currentUser/usr/local/bin/perl",
               "/usr/local/bin/perl", "/usr/bin/perl"]
candidates = list(dict.fromkeys(c for c in candidates if c))
MODS = ("use LWP::UserAgent; use HTTP::Daemon; use HTTP::Response; use URI; "
        "use JoeDog::Config; use FileHandle; "
        "print join(chr(10), map { $INC{$_} } qw(LWP/UserAgent.pm HTTP/Daemon.pm "
        "HTTP/Request.pm URI.pm JoeDog/Config.pm));")
perl = None
env_perl = None
tried = []
for cand in candidates:
    if not cand or not os.path.isfile(cand) or not os.access(cand, os.X_OK):
        continue
    env = dict(os.environ)
    # conanrun exports PERL5LIB of the (target-arch) perl dependency; a
    # different perl must not inherit it (arch-specific XS modules).
    own = env.get("PERL5LIB") if cand == shebang[2:].strip() else None
    env["PERL5LIB"] = os.pathsep.join([LIBDIR] + ([own] if own else []))
    try:
        r = subprocess.run([cand, "-e", MODS], env=env, capture_output=True,
                           text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        tried.append(f"{cand}: {exc}")
        continue
    if r.returncode == 0:
        perl, env_perl, loaded = cand, env, r.stdout.split()
        break
    tried.append(f"{cand}: {r.stderr.strip()[:160]}")
if not perl:
    fail("no runnable perl for the bundled libwww-perl; tried:\n  " + "\n  ".join(tried))
print("using perl:", perl, "| PERL5LIB:", env_perl["PERL5LIB"])
check(len(loaded) == 5 and all(p.startswith(LIBDIR + os.sep) for p in loaded),
      "LWP/HTTP::Daemon/HTTP::Request/URI/JoeDog::Config all resolve from the package lib/sproxy")


def run_sproxy(args, **kw):
    return subprocess.run([perl, SPROXY] + args, env=env_perl,
                          capture_output=True, text=True, timeout=60, **kw)


# ---- 1. banner / usage ----------------------------------------------------
print("[1/4] -V / -h")
r = run_sproxy(["-V"])
check(r.returncode == 0 and re.fullmatch(r"SPROXY v1\.02-[A-Z][a-z]+-\d\d-\d{4}", r.stdout.strip()),
      f"-V banner substituted: {r.stdout.strip()!r} (rc={r.returncode}, {r.stderr.strip()[:80]})")
r = run_sproxy(["-h"])
check(r.returncode == 0 and "sproxy v1.02-" in r.stdout and "-p NUM" in r.stdout,
      "-h prints usage with substituted version")
check(shebang.startswith("#!/") and "%_" not in shebang and "@" not in shebang,
      f"shebang rewritten from %_PERL%: {shebang}")

# ---- 2. origin server + proxy ---------------------------------------------
print("[2/4] start origin server and sproxy")
seen = []


class Origin(BaseHTTPRequestHandler):
    def _reply(self, body):
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        seen.append(("GET", self.path, ""))
        if self.path == "/page.html":
            data = b"<html><head><title>t</title></head><body>origin-HTML</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self._reply("origin-GET:" + self.path)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        seen.append(("POST", self.path, body))
        self._reply("origin-POST:" + body)

    def log_message(self, *a):
        pass


origin = ThreadingHTTPServer(("127.0.0.1", 0), Origin)
oport = origin.server_address[1]
threading.Thread(target=origin.serve_forever, daemon=True).start()

with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    pport = s.getsockname()[1]
with open(os.path.join(WORK, "BlockHtml.pm"), "w", encoding="utf-8") as fh:
    fh.write("package BlockHtml;\n"
             "unshift @INC, sub { die \"HTML::* blocked by test\\n\" "
             "if $_[1] =~ m{^HTML/}; return; };\n1;\n")
env_proxy = dict(env_perl)
env_proxy["PERL5OPT"] = f"-I{WORK} -MBlockHtml"
outfile = os.path.join(WORK, "sproxy-urls.txt")
if os.path.exists(outfile):
    os.remove(outfile)
proc = subprocess.Popen([perl, SPROXY, "-p", str(pport), "-o", outfile, "127.0.0.1"],
                        env=env_proxy, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
try:
    deadline = time.time() + 30
    while True:
        if proc.poll() is not None:
            fail("sproxy exited early: " + proc.stderr.read().decode()[:300])
        try:
            socket.create_connection(("127.0.0.1", pport), timeout=1).close()
            break
        except OSError:
            if time.time() > deadline:
                fail("sproxy did not open its listening port")
            time.sleep(0.2)
    print("  OK: sproxy listening on 127.0.0.1:%d" % pport)

    # ---- 3. requests through the proxy ------------------------------------
    print("[3/4] GET + POST + HTML through the proxy")
    base = f"http://127.0.0.1:{oport}"
    conn = http.client.HTTPConnection("127.0.0.1", pport, timeout=30)
    conn.request("GET", base + "/hello?x=1")
    resp = conn.getresponse()
    body = resp.read().decode()
    check(resp.status == 200 and body == "origin-GET:/hello?x=1",
          f"GET forwarded: {resp.status} {body!r}")
    conn.close()

    conn = http.client.HTTPConnection("127.0.0.1", pport, timeout=30)
    conn.request("POST", base + "/form", body="a=1\nb=2",
                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    resp = conn.getresponse()
    body = resp.read().decode()
    check(resp.status == 200 and body == "origin-POST:a=1\nb=2",
          f"POST forwarded: {resp.status} {body!r}")
    conn.close()
    conn = http.client.HTTPConnection("127.0.0.1", pport, timeout=30)
    conn.request("GET", base + "/page.html")
    resp = conn.getresponse()
    body = resp.read().decode()
    check(resp.status == 200 and "origin-HTML" in body
          and resp.getheader("Content-Type", "").startswith("text/html"),
          f"text/html forwarded with HTML::* unloadable: {resp.status} {body[:40]!r}")
    conn.close()
    check(("GET", "/hello?x=1", "") in seen and ("POST", "/form", "a=1\nb=2") in seen,
          "origin received both proxied requests")

    # ---- 4. URL log --------------------------------------------------------
    print("[4/4] sproxy URL log")
    want = {f"{base}/hello?x=1", f"{base}/form POST a=1&b=2", f"{base}/page.html"}
    got = set()
    deadline = time.time() + 15
    while time.time() < deadline:
        if os.path.exists(outfile):
            with open(outfile, encoding="utf-8") as fh:
                got = {ln.strip() for ln in fh if ln.strip()}
        if want <= got:
            break
        time.sleep(0.3)
    check(want <= got, f"output file has siege-style lines: {sorted(got)}")
finally:
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    origin.shutdown()

print("sproxy consumer test: 10 assertions passed")
