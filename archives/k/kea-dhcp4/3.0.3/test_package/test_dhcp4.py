#!/usr/bin/env python3
"""Consumer test for the packaged kea-dhcp4 3.0.3.

Runs the packaged DHCPv4 server (found through the Conan run environment) and
checks the contract a consumer depends on:

* the daemon starts at all -- which requires every Kea runtime library the
  binary needs to be reachable (a missing libkea-*.so aborts the process
  before main());
* the version, extended-version and configuration-report outputs of the
  Kea 3.0.3 release;
* the command-line error paths (missing configuration, unknown option);
* the configuration-check mode (-t): a minimal valid DHCPv4 configuration is
  accepted end to end (JSON parse -> mandatory Dhcp4 element -> all
  configuration handlers in check-only mode, no sockets opened) while broken
  inputs are rejected with the documented diagnostics.
"""
import os
import shutil
import subprocess
import sys
import tempfile

EXPECTED_VERSION = "3.0.3"

MINIMAL_CONFIG = """{
  "Dhcp4": {
    "interfaces-config": { "interfaces": [ "lo" ] },
    "lease-database": { "type": "memfile", "persist": false },
    "valid-lifetime": 3600,
    "subnet4": [
      {
        "id": 1,
        "subnet": "192.0.2.0/24",
        "pools": [ { "pool": "192.0.2.10 - 192.0.2.20" } ]
      }
    ]
  }
}
"""

failures = []
checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        failures.append(message)


KEA_DHCP4 = shutil.which("kea-dhcp4")
if not KEA_DHCP4:
    print("kea-dhcp4 is not on PATH - the package exposes no runnable command")
    sys.exit(1)
print("kea-dhcp4:", KEA_DHCP4)


def run(*args, **kwargs):
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    return subprocess.run([KEA_DHCP4, *args], capture_output=True, text=True,
                          timeout=120, **kwargs)


tmpdir = tempfile.mkdtemp(prefix="kea-dhcp4-consumer-")
good_cfg = os.path.join(tmpdir, "kea-dhcp4.conf")
with open(good_cfg, "w") as f:
    f.write(MINIMAL_CONFIG)
bad_json_cfg = os.path.join(tmpdir, "bad-json.conf")
with open(bad_json_cfg, "w") as f:
    f.write("{ this is not valid json\n")
no_dhcp4_cfg = os.path.join(tmpdir, "no-dhcp4.conf")
with open(no_dhcp4_cfg, "w") as f:
    f.write("{}\n")

# --- version output -----------------------------------------------------------
version = run("-v")
check(version.returncode == 0, f"-v exited with {version.returncode}")
check(version.stdout.strip() == EXPECTED_VERSION,
      f"-v printed {version.stdout.strip()!r}, expected {EXPECTED_VERSION!r}")

extended = run("-V")
check(extended.returncode == 0, f"-V exited with {extended.returncode}")
check(extended.stdout.strip().startswith(EXPECTED_VERSION),
      f"-V printed {extended.stdout.strip()!r}, expected the {EXPECTED_VERSION} extended version")
check("linked with:" in extended.stdout,
      "-V did not list the linked libraries")

# --- configuration report (-W) ------------------------------------------------
report = run("-W")
check(report.returncode == 0, f"-W exited with {report.returncode}")
check("Kea source configure results" in report.stdout,
      "-W did not print the build-time configuration report")

# --- command line error paths -------------------------------------------------
usage = run("-Z")
check(usage.returncode != 0,
      f"an unknown option exited with {usage.returncode}, expected a failure")
check("Usage: kea-dhcp4" in usage.stdout + usage.stderr,
      "an unknown option did not print the kea-dhcp4 usage text")

no_conf = run()
check(no_conf.returncode != 0,
      f"a bare invocation exited with {no_conf.returncode}, expected a failure")
check("Configuration file not specified." in no_conf.stdout + no_conf.stderr,
      "a bare invocation did not name the missing configuration file")

# --- configuration-check mode (-t, no sockets) --------------------------------
valid = run("-t", good_cfg)
check(valid.returncode == 0,
      f"a valid configuration failed the syntax check ({valid.returncode}): "
      f"{valid.stdout + valid.stderr}")
check("Error loading shared library" not in valid.stdout + valid.stderr,
      f"a Kea runtime library is missing: {valid.stdout + valid.stderr}")

verbose = run("-d", "-t", good_cfg)
check(verbose.returncode == 0,
      f"the verbose syntax check exited with {verbose.returncode}")
check("Syntax check OK" in verbose.stdout + verbose.stderr,
      "the verbose syntax check did not confirm the valid configuration")

broken = run("-t", bad_json_cfg)
check(broken.returncode != 0,
      f"a malformed JSON configuration exited with {broken.returncode}, "
      "expected a failure")
check("Syntax check failed" in broken.stdout + broken.stderr,
      "a malformed JSON configuration was not reported as a syntax failure")

missing = run("-t", no_dhcp4_cfg)
check(missing.returncode != 0,
      f"a configuration without the Dhcp4 element exited with "
      f"{missing.returncode}, expected a failure")
# An empty map is already rejected by the Dhcp4 grammar ("expecting Dhcp4");
# a configuration that parses but lacks the element would be rejected by the
# map-level check ("Missing mandatory Dhcp4 element").
missing_out = missing.stdout + missing.stderr
check("expecting Dhcp4" in missing_out
      or "Missing mandatory Dhcp4 element" in missing_out,
      f"a configuration without the Dhcp4 element was not rejected: "
      f"{missing_out!r}")

absent = run("-t", os.path.join(tmpdir, "does-not-exist.conf"))
check(absent.returncode != 0,
      f"a missing configuration file exited with {absent.returncode}, "
      "expected a failure")
check("Syntax check failed" in absent.stdout + absent.stderr
      or "No configuration found" in absent.stdout + absent.stderr,
      "a missing configuration file was not reported as a failure")

print(f"checks run: {checks}")
if failures:
    for failure in failures:
        print("FAIL:", failure)
    sys.exit(1)
print("all checks passed")
