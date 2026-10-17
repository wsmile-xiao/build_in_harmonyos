#!/usr/bin/env python3
"""Smoke test for the 24 SIMH simulator binaries on OHOS.

Feeds "show version\nquit\n" to every simulator in the package bin/ dir and
asserts the "<machine> simulator V3.12-3" banner plus a clean exit.  For
pdp11 additionally exercises the SCP deposit/examine path: deposit an octal
immediate into memory, single-step the CPU and verify the register write.
"""

import os
import subprocess
import sys

BINS = [
    "pdp1", "pdp4", "pdp7", "pdp8", "pdp9", "pdp15", "pdp11", "pdp10",
    "vax", "vax780", "nova", "eclipse", "i1401", "i1620", "altair", "gri",
    "i7094", "id16", "uc15", "id32", "sds", "lgp", "h316", "sigma",
]

passed = 0
failed = []
bindir = sys.argv[1]

for exe in BINS:
    path = os.path.join(bindir, exe)
    if not os.path.isfile(path):
        failed.append((exe, "binary missing in package bin/"))
        continue
    try:
        r = subprocess.run(
            [path],
            input="show version\nquit\n",
            capture_output=True,
            text=True,
            timeout=60,
        )
        out = r.stdout + r.stderr
        if "simulator V3.12-3" in out and r.returncode == 0:
            passed += 1
        else:
            failed.append((exe, "banner/exit check failed: %r rc=%d" % (out[:120], r.returncode)))
    except Exception as exc:  # noqa: BLE001
        failed.append((exe, "run error: %s" % exc))

# Functional check on pdp11: MOV #0173,R0 (012700 000173), single-step, read R0.
pdp11 = os.path.join(bindir, "pdp11")
if os.path.isfile(pdp11):
    script = (
        "deposit 1000 012700\n"
        "deposit 1002 000173\n"
        "deposit pc 1000\n"
        "step 2\n"
        "examine r0\n"
        "quit\n"
    )
    try:
        r = subprocess.run(
            [pdp11], input=script, capture_output=True, text=True, timeout=60
        )
        out = r.stdout + r.stderr
        if "R0:\t000173" in out or "R0: 000173" in out:
            passed += 1
        else:
            failed.append(("pdp11-deposit/step", "register check failed: %r" % out[-200:]))
    except Exception as exc:  # noqa: BLE001
        failed.append(("pdp11-deposit/step", "run error: %s" % exc))
else:
    failed.append(("pdp11-deposit/step", "pdp11 binary missing"))

print("SIMH smoke test: %d/%d assertions passed" % (passed, len(BINS) + 1))
if failed:
    for name, why in failed:
        print("FAILED: %s — %s" % (name, why))
    sys.exit(1)
print("All simulator banners and pdp11 register deposit/step verified.")
