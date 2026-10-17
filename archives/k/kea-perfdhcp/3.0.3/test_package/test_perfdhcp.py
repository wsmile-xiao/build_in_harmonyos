#!/usr/bin/env python3
"""Consumer test for the packaged kea-perfdhcp 3.0.3.

Runs the packaged command-line client (found through the Conan run environment)
and checks the contract a consumer depends on:

* the tool starts at all -- which requires every Kea runtime library the binary
  needs to be reachable (a missing libkea-*.so aborts the process before main());
* the version and extended-version outputs of the Kea 3.0.3 release;
* the usage text and the command-line error path;
* one real exchange attempt end to end (option parsing -> socket -> rate
  control -> statistics report), which is the code path the benchmarks use.
"""
import shutil
import subprocess
import sys

EXPECTED_VERSION = "3.0.3"
# perfdhcp exit statuses (src/bin/perfdhcp/command_options.cc usage text):
# 0 complete success, 1 general error, 2 command-line error, 3 incomplete exchanges.
EXIT_INCOMPLETE_EXCHANGES = 3

failures = []
checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        failures.append(message)


PERFDHCP = shutil.which("perfdhcp")
if not PERFDHCP:
    print("perfdhcp is not on PATH - the package exposes no runnable command")
    sys.exit(1)
print("perfdhcp:", PERFDHCP)


def run(*args, **kwargs):
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    return subprocess.run([PERFDHCP, *args], capture_output=True, text=True,
                          timeout=60, **kwargs)


# --- version output -----------------------------------------------------------
version = run("-v")
check(version.returncode == 0, f"-v exited with {version.returncode}")
check(version.stdout.strip() == EXPECTED_VERSION,
      f"-v printed {version.stdout.strip()!r}, expected {EXPECTED_VERSION!r}")

extended = run("-V")
check(extended.returncode == 0, f"-V exited with {extended.returncode}")
check(extended.stdout.strip().startswith(EXPECTED_VERSION),
      f"-V printed {extended.stdout.strip()!r}, expected the {EXPECTED_VERSION} extended version")

# --- usage / option parser ----------------------------------------------------
usage = run("-h")
check(usage.returncode == 0, f"-h exited with {usage.returncode}")
check("perfdhcp" in usage.stdout and "--scenario" in usage.stdout,
      "-h did not print the perfdhcp usage text")

bad = run("--scenario", "bogus", "::1")
check(bad.returncode != 0,
      f"an invalid --scenario value exited with {bad.returncode}, expected a failure")
check("scenario value 'bogus' is wrong" in bad.stdout + bad.stderr,
      "the option parser did not reject the invalid scenario value")

# --- one end-to-end exchange attempt ------------------------------------------
# No DHCPv6 server answers on the loopback address, so the run is expected to
# finish with "incomplete exchanges" (3) -- reaching that point proves the client
# loaded its Kea runtime libraries, parsed the options, opened the socket and ran
# the rate-controlled exchange loop.  A DHCPv6 server that happens to listen on
# the chosen port would turn it into a complete run (0), which is accepted too.
attempt = run("-6", "-r", "1", "-n", "1", "-D", "1", "-L", "30547", "::1")
check(attempt.returncode in (0, EXIT_INCOMPLETE_EXCHANGES),
      f"the exchange attempt exited with {attempt.returncode}, expected 0 or "
      f"{EXIT_INCOMPLETE_EXCHANGES}: {attempt.stderr.strip()}")
check("Error loading shared library" not in attempt.stderr,
      f"a Kea runtime library is missing: {attempt.stderr.strip()}")
check("Statistics for:" in attempt.stdout + attempt.stderr,
      "the run produced no statistics report")

print(f"checks run: {checks}")
if failures:
    for failure in failures:
        print("FAIL:", failure)
    sys.exit(1)
print("all checks passed")
