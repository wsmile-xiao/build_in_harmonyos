#!/usr/bin/env python3
"""Consumer test for the packaged kea-dhcp6 3.0.3.

Runs the packaged server (found through the Conan run environment) and checks
the contract a consumer depends on:

* the tool starts at all -- which requires every Kea runtime library the binary
  needs to be reachable (a missing libkea-*.so aborts the process before main());
* the version and extended-version outputs of the Kea 3.0.3 release;
* the build-time configuration report (-W);
* the syntax-check path (-t) on a valid configuration and on two invalid inputs,
  which is the code path every deployment runs before starting the server;
* the usage text and the command-line error path.

Executor contract: every case prints one "TEST <name> PASS" or
"TEST <name> FAIL" line, the run ends with a "TEST SUMMARY: N passed,
M failed" line, and the process exits 1 if any case failed.
"""
import json
import os
import shutil
import subprocess
import sys

EXPECTED_VERSION = "3.0.3"

checks = 0
failures = 0


def check(name, condition, detail=""):
    """Run one named test case and print its verdict line."""
    global checks, failures
    checks += 1
    if condition:
        print(f"TEST {name} PASS")
    else:
        failures += 1
        line = f"TEST {name} FAIL"
        if detail:
            line += f": {detail}"
        print(line)


def summary():
    print(f"TEST SUMMARY: {checks - failures} passed, {failures} failed")


KEA = shutil.which("kea-dhcp6")
if not KEA:
    print("TEST kea-dhcp6 on PATH FAIL: the package exposes no runnable command")
    print("TEST SUMMARY: 0 passed, 1 failed")
    sys.exit(1)
print(f"info - kea-dhcp6: {KEA}")


def workdir():
    """Pick a writable directory for the throw-away config files.

    TMPDIR comes first (the recipe's test sandbox sets it on the device), then
    the current directory of the consumer test build (always writable, and the
    right fallback on HarmonyOS PC where /tmp is read-only).
    """
    for cand in (os.environ.get("TMPDIR"), os.getcwd()):
        if not cand or not os.path.isdir(cand):
            continue
        probe = os.path.join(cand, ".kea_dhcp6_write_probe")
        try:
            with open(probe, "w") as fh:
                fh.write("x")
            os.remove(probe)
            return cand
        except OSError:
            continue
    return None


WORKDIR = workdir()
if WORKDIR is None:
    print("TEST writable workdir FAIL: no writable directory for the "
          "test configuration files")
    print("TEST SUMMARY: 0 passed, 1 failed")
    sys.exit(1)


def write_cfg(name, config):
    path = os.path.join(WORKDIR, name)
    with open(path, "w") as fh:
        json.dump(config, fh)
    return path


def run(*args, **kwargs):
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    return subprocess.run([KEA, *args], capture_output=True, text=True,
                          timeout=120, **kwargs)


def combined(result):
    return result.stdout + result.stderr


# --- version output -----------------------------------------------------------
version = run("-v")
check("-v exit status", version.returncode == 0,
      f"exited with {version.returncode}")
check("-v version output", version.stdout.strip() == EXPECTED_VERSION,
      f"printed {version.stdout.strip()!r}, expected {EXPECTED_VERSION!r}")
check("-v runtime closure", "Error loading shared library" not in version.stderr,
      f"a Kea runtime library is missing: {version.stderr.strip()}")

extended = run("-V")
check("-V exit status", extended.returncode == 0,
      f"exited with {extended.returncode}")
check("-V extended version", extended.stdout.strip().startswith(EXPECTED_VERSION),
      f"printed {extended.stdout.strip()!r}, "
      f"expected the {EXPECTED_VERSION} extended version")

# --- build-time configuration report ------------------------------------------
report = run("-W")
check("-W exit status", report.returncode == 0,
      f"exited with {report.returncode}")
check("-W configure report", "Kea source configure results" in combined(report),
      "-W did not print the Kea configuration report")

# --- syntax check: valid configuration ----------------------------------------
# A Dhcp6 configuration with the protocol-required "Dhcp6" node and an empty
# subnet list is valid for -t; the server performs the full parse + validation
# and exits 0 without opening any socket.
valid_path = write_cfg("kea_dhcp6_valid.json", {"Dhcp6": {"subnet6": []}})
valid = run("-t", valid_path)
check("-t valid configuration exit status", valid.returncode == 0,
      f"-t on a valid configuration exited with {valid.returncode}: "
      f"{combined(valid).strip()}")
check("-t valid configuration runtime closure",
      "Error loading shared library" not in valid.stderr,
      f"a Kea runtime library is missing: {valid.stderr.strip()}")

# --- syntax check: invalid subnet ---------------------------------------------
bad_path = write_cfg("kea_dhcp6_bad_subnet.json",
                     {"Dhcp6": {"subnet6": [{"subnet": "not-a-subnet"}]}})
bad = run("-t", bad_path)
check("-t invalid subnet exit status", bad.returncode != 0,
      f"-t on an invalid subnet exited with {bad.returncode}, "
      "expected a failure")
check("-t invalid subnet message", "Invalid subnet syntax" in combined(bad),
      "the syntax check did not report the invalid subnet")

# --- syntax check: missing file ------------------------------------------------
# Unlike -c, -t on a missing file is handled before the daemon starts.
missing = run("-t", os.path.join(WORKDIR, "kea_dhcp6_does_not_exist.json"))
check("-t missing file exit status", missing.returncode != 0,
      f"-t on a missing file exited with {missing.returncode}, "
      "expected a failure")
check("-t missing file message", "Unable to open file" in combined(missing),
      "the syntax check did not report the unreadable configuration file")

# --- usage / option parser ------------------------------------------------------
badopt = run("-z")
check("-z unknown option exit status", badopt.returncode != 0,
      f"an unrecognized option exited with {badopt.returncode}, "
      "expected a failure")
check("-z unknown option message", "unrecognized option" in combined(badopt),
      "the option parser did not reject the unrecognized option")
check("-z usage text", "Usage: kea-dhcp6" in combined(badopt),
      "the option parser did not print the kea-dhcp6 usage text")

summary()
sys.exit(1 if failures else 0)
