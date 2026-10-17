#!/usr/bin/env python3
"""Consumer test for vfit 2.1.0 — exercises real API (not a stub)."""

import json
import os
import subprocess
import sys
import tempfile

checks = 0


def check(cond, msg):
    global checks
    if not cond:
        raise AssertionError(msg)
    print(f"PASS: {msg}")
    checks += 1


# 1. import vfit package and submodules
import vfit
import vfit.app
import vfit.util

check(hasattr(vfit, "__file__"), "import vfit")

# 2. app.loadConfig parses JSON and defaults subfamily to Regular
sample_cfg = [
    {"family": "TestFamily", "axes": {"wght": 400.0}, "prefFamily": "TestFamily", "prefSubfamily": "Regular"}
]
with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
    json.dump(sample_cfg, tf)
    cfg_path = tf.name
try:
    cfg = vfit.app.loadConfig(cfg_path)
    check(isinstance(cfg, list) and cfg[0].get("subfamily") == "Regular", "loadConfig default subfamily Regular")
finally:
    os.unlink(cfg_path)

# 3. util.sanitize removes spaces
check(vfit.util.sanitize("A B C") == "ABC", "util.sanitize removes spaces")

# 4. util.getPostscriptName builds PS name
style = {"family": "My Family", "subfamily": "Bold", "prefFamily": "MyFamily", "prefSubfamily": "Bold"}
check(vfit.util.getPostscriptName(style) == "MyFamily-Bold", "getPostscriptName MyFamily-Bold")

# 5. util.getMacStyle mapping
check(vfit.util.getMacStyle("Regular") == 0 and vfit.util.getMacStyle("Bold") == 1, "getMacStyle Regular/Bold")

# 6. util.makeSelection for Regular sets bit 6
check(vfit.util.makeSelection(0, "Regular") == 0b1000000, "makeSelection Regular => 64")

# 7. CLI --help is reachable (via bin/vfit or python -m)
vfit_bin = None
for d in os.environ.get("PATH", "").split(os.pathsep):
    cand = os.path.join(d, "vfit")
    if os.path.isfile(cand):
        vfit_bin = cand
        break
if vfit_bin:
    proc = subprocess.run([vfit_bin, "--help"], capture_output=True, text=True)
else:
    proc = subprocess.run([sys.executable, "-m", "vfit.app", "--help"], capture_output=True, text=True)
check(proc.returncode == 0 and "vfit" in (proc.stdout + proc.stderr).lower(), "vfit --help exits 0")

# 8. util.dropVariationTables removes fvar/gvar on a dummy TTFont
from fontTools.ttLib import TTFont

font = TTFont()
font["fvar"] = object()
font["gvar"] = object()
vfit.util.dropVariationTables(font)
check("fvar" not in font and "gvar" not in font, "dropVariationTables removes fvar/gvar")

expected = 8
if checks != expected:
    raise AssertionError(f"assertion count mismatch: expected {expected}, got {checks}")
print(f"PASS: vfit consumer test ({checks}/{expected} assertions)")
