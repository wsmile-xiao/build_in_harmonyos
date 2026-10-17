#!/usr/bin/env python3
"""Consumer test for igor2 0.5.9 — validates real API against the installed package.

Tests (R34: substantively depend on the tested package):
  1. binarywave.load on a real IGOR binary wave (mac-double.ibw from the
     upstream test-suite data, 182 bytes, base64-embedded) — verifies
     version / wData values / wave_header fields against upstream-expected
     values (parity with upstream test_ibw.py).
  2. packed.load on a real IGOR packed experiment (.pxp) header — the
     first record is a version record (parity with upstream test_pxp.py).
  3. bin/igorbinarywave CLI wrapper: converts the .ibw to tab-separated
     ASCII (upstream CLI contract: numpy.savetxt fmt="%g").

numpy is provided by the host python3 runtime (badread precedent).
"""
import base64
import os
import subprocess
import sys
import tempfile

# E002: /tmp is read-only on OHOS — honor injected TMPDIR
_tmpdir = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
if _tmpdir:
    try:
        os.makedirs(_tmpdir, exist_ok=True)
        tempfile.tempdir = _tmpdir
    except Exception:
        pass

pkg = sys.argv[1] if len(sys.argv) > 1 else ""
if pkg:
    py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    site = os.path.join(pkg, "lib", py_ver, "site-packages")
    if not os.path.isdir(os.path.join(site, "igor2")):
        raise SystemExit(f"FAIL: igor2 not installed at {site}")
    sys.path.insert(0, site)

# verify we import the packaged igor2, not a stray source tree
import igor2  # noqa: E402
from igor2.binarywave import load as loadibw  # noqa: E402
from igor2.packed import load as loadpxp  # noqa: E402

mod_file = os.path.realpath(igor2.__file__)
if pkg and not mod_file.startswith(os.path.realpath(pkg)):
    raise SystemExit(f"FAIL: igor2 imported from {mod_file}, not from package {pkg}")

# upstream tests/data/mac-double.ibw (182 bytes) — real IGOR binary wave
MAC_DOUBLE_IBW_B64 = (
    "AAIAAACmAAAAAAAAAABiMQAEAAAAAGRvdWJsZQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUAAD/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAALLomIIAALLomIIAAAAAQBQAAAAAAABAEAAAAAAAAEAIAAAAAAAAQAAAAAAAAAA/8AAAAAAAAAAAAAAAAAAAAAAAACNCAAA="
)

# upstream tests/data/packed-byteorder.pxt header (first 20 bytes = first
# record boundary, big-endian) — real IGOR packed experiment record
PXT_PREFIX_B64 = "AAEAAAAAAAwAAgAAAAAAAAAAAAA="

failures = []

# ── Test 1: binarywave.load on a real .ibw (upstream test_ibw parity) ──
try:
    with tempfile.NamedTemporaryFile(suffix=".ibw", delete=False) as fh:
        fh.write(base64.b64decode(MAC_DOUBLE_IBW_B64))
        ibw_path = fh.name
    try:
        data = loadibw(ibw_path)
        wave = data["wave"]
        assert data["version"] == 2, f"version: {data['version']}"
        wdata = list(wave["wData"])
        assert wdata == [5.0, 4.0, 3.0, 2.0, 1.0], f"wData: {wdata}"
        wh = wave["wave_header"]
        assert wh["bname"] == b"double", f"bname: {wh['bname']}"
        assert wh["npnts"] == 5, f"npnts: {wh['npnts']}"
        assert wh["type"] == 4, f"type: {wh['type']}"  # NT_FP64
        assert wave["bin_header"]["wfmSize"] == 166, "wfmSize"
        print("PASS 1: binarywave.load real .ibw (version=2, wData=[5..1], bname=double, npnts=5)")
    finally:
        os.unlink(ibw_path)
except Exception as exc:  # noqa: BLE001
    failures.append(f"binarywave.load: {exc!r}")

# ── Test 2: packed.load on a real .pxp record (upstream test_pxt parity) ──
try:
    with tempfile.NamedTemporaryFile(suffix=".pxp", delete=False) as fh:
        fh.write(base64.b64decode(PXT_PREFIX_B64))
        pxp_path = fh.name
    try:
        records, version = loadpxp(pxp_path, ignore_unknown=True,
                                   initial_byte_order=">")
        assert len(records) == 1, f"records: {len(records)}"
        r0 = records[0]
        assert type(r0).__name__ == "VariablesRecord", type(r0).__name__
        expected = {
            "version": 2,
            "variables": {
                "var_header": {"numSysVars": 0, "numUserVars": 0,
                               "numUserStrs": 0, "numDependentVars": 0,
                               "numDependentStrs": 0},
                "sysVars": {}, "userVars": {}, "userStrs": {},
                "dependentVars": [], "dependentStrs": []}}
        assert r0.variables == expected, f"variables: {r0.variables}"
        print("PASS 2: packed.load real .pxp record (VariablesRecord, version=2)")
    finally:
        os.unlink(pxp_path)
except Exception as exc:  # noqa: BLE001
    failures.append(f"packed.load: {exc!r}")

# ── Test 3: bin/igorbinarywave CLI wrapper end-to-end ──
try:
    with tempfile.NamedTemporaryFile(suffix=".ibw", delete=False) as fh:
        fh.write(base64.b64decode(MAC_DOUBLE_IBW_B64))
        ibw_path = fh.name
    out_path = ibw_path + ".txt"
    try:
        wrapper = os.path.join(pkg, "bin", "igorbinarywave") if pkg else "igorbinarywave"
        r = subprocess.run(
            [wrapper, "-f", ibw_path, "-o", out_path],
            capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, (
            f"CLI exit={r.returncode} stderr={r.stderr[-200:]!r}")
        txt = open(out_path).read().strip()
        assert txt == "5\n4\n3\n2\n1", f"CLI output: {txt!r}"
        print("PASS 3: igorbinarywave CLI wrapper (ibw -> ASCII '5 4 3 2 1')")
    finally:
        os.unlink(ibw_path)
        if os.path.exists(out_path):
            os.unlink(out_path)
except Exception as exc:  # noqa: BLE001
    failures.append(f"CLI wrapper: {exc!r}")

if failures:
    for f in failures:
        print(f"FAIL: {f}", file=sys.stderr)
    sys.exit(1)
print(f"igor2 consumer test: 3/3 passed (module: {mod_file})")
