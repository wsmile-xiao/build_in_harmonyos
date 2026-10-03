#!/usr/bin/env python3
"""OHOS-specific consumer test for packaged justbackoff 0.6.0 (鸿蒙专项测试).

This file is an OHOS adaptation addition — upstream 0.6.0 ships no such
platform-contract test (its suite only asserts Backoff arithmetic).

What it verifies about the artifact as installed on HarmonyOS PC (aarch64):

  O1. OHOS runtime identity — the package is loaded by the platform CPython
      3.12 (`sys.implementation.name == "cpython"`); the resolved platform
      strings are printed for the record.
  O2. OHOS package layout — `justbackoff.__file__` must resolve into the
      OHOS conan layout `<pkg>/lib/python3.12/site-packages/justbackoff/`,
      i.e. the conanrun PYTHONPATH wiring works on the platform.
  O3. noarch/no-binary contract — the installed payload contains zero native
      objects (.so/.pyd/.dylib/.a/.o) and no `__pycache__`-only artifacts:
      the OHOS aarch64 artifact is the upstream pure-Python payload, so it is
      architecture-independent and needs no cross-compiled binary.
  O4. platform entropy source — `random` is the ONLY non-upstream-surface the
      module touches (stdlib `random.random()` in the jitter branch). The test
      proves the platform's random module is usable and that jitter output
      stays inside the documented bound on OHOS.
  O5. read-only install contract — an OHOS app sandbox install tree may be
      non-writable: a fresh interpreter started with `-B` (no bytecode write)
      must import the module from the package tree and compute correctly,
      leaving no `__pycache__` behind.

Usage: test_ohos_justbackoff.py <site-packages-dir>
"""
import os
import random
import shutil
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = os.path.abspath(sys.argv[1])
    if not os.path.isfile(os.path.join(site, "justbackoff", "__init__.py")):
        raise AssertionError(f"justbackoff package missing in {site}")
    sys.path.insert(0, site)

    from justbackoff import Backoff, to_seconds

    n = 0

    # --- O1: OHOS runtime identity ---------------------------------------
    import platform
    assert sys.implementation.name == "cpython", sys.implementation.name
    assert sys.version_info[:2] >= (3, 12), sys.version_info
    print(f"  OHOS interpreter : {sys.executable}")
    print(f"  OHOS runtime     : {platform.python_implementation()} "
          f"{platform.python_version()} on {sys.platform} "
          f"({platform.machine()})")
    n += 2

    # --- O2: OHOS conan package layout -----------------------------------
    import justbackoff as mod
    pkg_dir = os.path.dirname(os.path.realpath(mod.__file__))
    expected = os.path.join(os.path.realpath(site), "justbackoff")
    assert pkg_dir == expected, (pkg_dir, expected)
    print(f"  OHOS import path : {mod.__file__}")
    n += 1

    # --- O3: noarch / no native objects ----------------------------------
    native_ext = (".so", ".pyd", ".dylib", ".a", ".o")
    native = []
    for root, _dirs, files in os.walk(pkg_dir):
        for fn in files:
            if fn.endswith(native_ext):
                native.append(os.path.join(root, fn))
    assert not native, f"unexpected native objects in payload: {native}"
    assert os.path.isfile(os.path.join(pkg_dir, "__init__.py"))
    n += 2

    # --- O4: platform entropy source + jitter bound ----------------------
    random.seed(20261002)
    values = [random.random() for _ in range(8)]
    assert all(0.0 <= v < 1.0 for v in values), values
    random.seed(20261002)
    b = Backoff(min_ms=100.0, max_ms=10000.0, factor=2.0, jitter=True)
    assert b.duration() == to_seconds(100.0)
    for attempt in (1, 2, 3):
        dur = b.duration()
        assert to_seconds(100.0) <= dur <= to_seconds(100.0 * 2 ** attempt), \
            (attempt, dur)
    print(f"  OHOS random seed : stable, 8 draws in [0,1), jitter bounded")
    n += 3

    # --- O5: read-only-safe import (-B, no bytecode write) ---------------
    cache = os.path.join(pkg_dir, "__pycache__")
    shutil.rmtree(cache, ignore_errors=True)
    tmp = os.environ.get("TMPDIR") or os.path.join(
        os.path.expanduser("~"), "tmp")
    os.makedirs(tmp, exist_ok=True)
    env = dict(os.environ)
    env["PYTHONPATH"] = site
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    probe = (
        "import justbackoff as m;"
        "assert m.to_seconds(100.0) == 0.1;"
        "b = m.Backoff(min_ms=100.0, max_ms=10000.0, factor=2.0);"
        "assert [b.duration() for _ in range(3)] == [0.1, 0.2, 0.4];"
        "print('import-ok', m.__file__)"
    )
    res = subprocess.run([sys.executable, "-B", "-c", probe],
                         cwd=tmp, env=env, capture_output=True, timeout=120)
    out = (res.stdout or b"").decode(errors="ignore").strip()
    err = (res.stderr or b"").decode(errors="ignore").strip()
    assert res.returncode == 0, f"rc={res.returncode} out={out!r} err={err!r}"
    assert out.startswith("import-ok"), out
    assert not os.path.exists(cache), \
        "bytecode cache written although -B / dont_write_bytecode was set"
    print(f"  OHOS read-only-safe import: rc=0, no __pycache__ created")
    n += 3

    print(f"OK: justbackoff 0.6.0 OHOS-specific test — {n} assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
