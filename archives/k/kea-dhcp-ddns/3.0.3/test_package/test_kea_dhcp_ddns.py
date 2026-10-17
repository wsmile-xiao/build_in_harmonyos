#!/usr/bin/env python3
"""Consumer test for the packaged kea-dhcp-ddns 3.0.3.

Runs the packaged command-line daemon (found through the Conan run
environment) and checks the contract a consumer depends on:

* the tool starts at all -- which requires every Kea runtime library the
  binary needs to be reachable (a missing libkea-*.so aborts the process
  before main());
* the version output of the Kea 3.0.3 release, both through the stock -v and
  through the GNU-style --version/--help aliases this package adds (the
  OpenHarmony PC packaging tool-chain probes packaged executables with the
  long spellings);
* the three configuration syntax-check paths that upstream's own process
  suite (d2_process_tests.sh) drives: a valid configuration exits 0, a
  syntactically broken one and an out-of-range port exit 1;
* one real daemon lifecycle end to end: start with -c, wait for the
  DCTL_CONFIG_COMPLETE message in its log, stop with SIGTERM and see
  DCTL_SHUTDOWN -- the full controller/queue-manager code path of the D2
  process.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

EXPECTED_VERSION = "3.0.3"
# The daemon binds this loopback port for the lifecycle test.  Upstream's own
# d2_process_tests.sh uses 127.0.0.1:53001; the consumer test moves out of the
# way to 53002 so the two suites can never collide.
TEST_PORT = 53002
START_TIMEOUT = 20.0
SHUTDOWN_TIMEOUT = 15.0

failures = []
checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        failures.append(message)


def pick_workdir():
    """A writable scratch directory (the device /tmp can be read-only)."""
    for env in ("TMPDIR", "TEMP", "TMP"):
        candidate = os.environ.get(env)
        if candidate and os.path.isdir(candidate) and os.access(candidate, os.W_OK):
            return candidate
    if os.path.isdir("/tmp") and os.access("/tmp", os.W_OK):
        return "/tmp"
    return os.getcwd()


KEA_DHCP_DDNS = shutil.which("kea-dhcp-ddns")
if not KEA_DHCP_DDNS:
    print("kea-dhcp-ddns is not on PATH - the package exposes no runnable command")
    sys.exit(1)
print("kea-dhcp-ddns:", KEA_DHCP_DDNS)

workdir = tempfile.mkdtemp(prefix="kea-d2-test-", dir=pick_workdir())
logfile = os.path.join(workdir, "d2.log")

# Relocate the daemon's runtime state next to the test.  KEA_LOG_FILE_DIR is
# authoritative for the logger output-path validation: without it the daemon
# only accepts paths under the build-time default (/var/log/kea), which does
# not exist for a package installed under any prefix.  KEA_PIDFILE_DIR and
# KEA_LOCKFILE_DIR keep the PID/lock files in the workdir as well.
test_env = dict(os.environ)
test_env["KEA_LOG_FILE_DIR"] = workdir
test_env["KEA_PIDFILE_DIR"] = workdir
test_env["KEA_LOCKFILE_DIR"] = workdir


def write_config(name, port):
    """Write a minimal, upstream-shaped D2 configuration and return its path."""
    path = os.path.join(workdir, name)
    config = {
        "DhcpDdns": {
            "ip-address": "127.0.0.1",
            "port": port,
            "tsig-keys": [],
            "forward-ddns": {},
            "reverse-ddns": {},
            "loggers": [
                {
                    "name": "kea-dhcp-ddns",
                    "output-options": [{"output": logfile}],
                    "severity": "DEBUG",
                }
            ],
        }
    }
    with open(path, "w") as f:
        json.dump(config, f)
    return path


def run(*args, **kwargs):
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    kwargs.setdefault("env", test_env)
    return subprocess.run([KEA_DHCP_DDNS, *args], capture_output=True, text=True,
                          timeout=60, **kwargs)


# --- version output -----------------------------------------------------------
version = run("-v")
check(version.returncode == 0, f"-v exited with {version.returncode}")
check(version.stdout.strip() == EXPECTED_VERSION,
      f"-v printed {version.stdout.strip()!r}, expected {EXPECTED_VERSION!r}")

# The GNU-style aliases this package adds (platform smoke-gate contract):
# --version behaves exactly like -v, --help prints the usage text, both exit 0.
long_version = run("--version")
check(long_version.returncode == 0,
      f"--version exited with {long_version.returncode}")
check(long_version.stdout.strip() == EXPECTED_VERSION,
      f"--version printed {long_version.stdout.strip()!r}, "
      f"expected {EXPECTED_VERSION!r}")

long_help = run("--help")
check(long_help.returncode == 0, f"--help exited with {long_help.returncode}")
check("Usage: kea-dhcp-ddns" in (long_help.stdout + long_help.stderr),
      "--help did not print the usage text")

# --- configuration syntax checks (the upstream process-test paths) ------------
good_cfg = write_config("good.json", TEST_PORT)
good = run("-t", good_cfg)
check(good.returncode == 0,
      f"-t on a valid configuration exited with {good.returncode}: "
      f"{good.stdout.strip()} {good.stderr.strip()}")

# port BOGUS: syntactically invalid JSON (upstream's CONFIG_BAD_SYNTAX)
bad_syntax_cfg = os.path.join(workdir, "bad_syntax.json")
with open(bad_syntax_cfg, "w") as f:
    f.write('{"DhcpDdns": {"ip-address": "127.0.0.1", "port": BOGUS, '
            '"tsig-keys": [], "forward-ddns": {}, "reverse-ddns": {}}}')
bad_syntax = run("-t", bad_syntax_cfg)
check(bad_syntax.returncode == 1,
      f"-t on a syntactically broken configuration exited with "
      f"{bad_syntax.returncode}, expected 1")

# port 80000: out of the valid port range (upstream's CONFIG_BAD_VALUE)
bad_value_cfg = write_config("bad_value.json", 80000)
bad_value = run("-t", bad_value_cfg)
check(bad_value.returncode == 1,
      f"-t on an out-of-range port exited with {bad_value.returncode}, "
      f"expected 1")

# --- one real daemon lifecycle -------------------------------------------------
if os.path.exists(logfile):
    os.remove(logfile)
proc = subprocess.Popen([KEA_DHCP_DDNS, "-c", good_cfg], env=test_env,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True)

configured = False
deadline = time.time() + START_TIMEOUT
while time.time() < deadline:
    if proc.poll() is not None:
        break
    if os.path.exists(logfile):
        with open(logfile) as f:
            if "DCTL_CONFIG_COMPLETE" in f.read():
                configured = True
                break
    time.sleep(0.25)

check(proc.poll() is None, "the daemon stayed running after startup")
check(configured, f"DCTL_CONFIG_COMPLETE logged within {START_TIMEOUT:.0f} s")
check(any(name.endswith(".pid") for name in os.listdir(workdir)),
      "the daemon wrote its PID file into KEA_PIDFILE_DIR")

if proc.poll() is None:
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=SHUTDOWN_TIMEOUT)
        exited_gracefully = True
    except subprocess.TimeoutExpired:
        exited_gracefully = False
        proc.kill()
        proc.wait()
else:
    exited_gracefully = False

check(exited_gracefully,
      f"the daemon exited within {SHUTDOWN_TIMEOUT:.0f} s of SIGTERM")

log_content = ""
if os.path.exists(logfile):
    with open(logfile) as f:
        log_content = f.read()
check("DCTL_SHUTDOWN" in log_content, "DCTL_SHUTDOWN logged on the way out")

_, daemon_stderr = proc.communicate(timeout=10)
seen_stderr = (version.stderr + good.stderr + bad_syntax.stderr
               + bad_value.stderr + (daemon_stderr or ""))
check("Error loading shared library" not in seen_stderr,
      f"a Kea runtime library is missing: {seen_stderr.strip()}")

print(f"checks run: {checks}")
if failures:
    for failure in failures:
        print("FAIL:", failure)
    sys.exit(1)
print("all checks passed")
