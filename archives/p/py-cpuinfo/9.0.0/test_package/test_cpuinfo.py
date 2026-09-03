#!/usr/bin/env python3
"""Consumer test for py-cpuinfo 9.0.0 — import + API + CLI smoke tests.

Tests:
1. Import cpuinfo module
2. Call get_cpu_info() API
3. Check returned dict has required keys
4. Run `cpuinfo` CLI and verify output
"""
import sys
import subprocess
from pathlib import Path

# Test 1: Import module
try:
    import cpuinfo
    print("[PASS] Import cpuinfo module")
except ImportError as e:
    print(f"[FAIL] Import cpuinfo: {e}")
    sys.exit(1)

# Test 2: Call get_cpu_info() API
try:
    info = cpuinfo.get_cpu_info()
    assert isinstance(info, dict), f"Expected dict, got {type(info)}"
    print(f"[PASS] get_cpu_info() returned dict with {len(info)} keys")
except Exception as e:
    print(f"[FAIL] get_cpu_info(): {e}")
    sys.exit(1)

# Test 3: Check required keys exist
required_keys = ["arch", "bits", "count"]
missing = [k for k in required_keys if k not in info]
if missing:
    print(f"[FAIL] Missing required keys in get_cpu_info(): {missing}")
    sys.exit(1)
print(f"[PASS] All required keys present: {required_keys}")
if "brand_raw" not in info:
    print("[WARN] Optional key 'brand_raw' is unavailable on this Worker")

# Test 4: Run CLI `cpuinfo`
try:
    cli_path = Path(cpuinfo.__file__).resolve().parents[4] / "bin" / "cpuinfo"
    result = subprocess.run(
        [str(cli_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        print(f"[FAIL] cpuinfo CLI exited {result.returncode}")
        print(result.stderr)
        sys.exit(1)
    output = result.stdout
    if len(output) < 50:
        print(f"[FAIL] cpuinfo output too short: {len(output)} bytes")
        sys.exit(1)
    # Check CLI output contains same keys as API
    for key in required_keys:
        if key not in output.lower():
            print(f"[WARN] CLI output missing key '{key}'")
    print(f"[PASS] cpuinfo CLI ran successfully, {len(output)} bytes output")
except subprocess.TimeoutExpired:
    print("[FAIL] cpuinfo CLI timeout")
    sys.exit(1)
except Exception as e:
    print(f"[FAIL] cpuinfo CLI: {e}")
    sys.exit(1)

print("\n=== All consumer tests passed ===")
sys.exit(0)
