"""test_unicorn.py — consumer test for unicorn 2.1.4.

1) Verifies the unicorn Python bindings import and uc_version() works.
2) Runs the upstream regress unit test arm64_reg_rw_w0_w30.py (real upstream
   test case, aarch64 build) via the packaged lib.
Usage: test_unicorn.py <site-packages> [<regress-test-dir>]
"""
import os
import subprocess
import sys

site = sys.argv[1] if len(sys.argv) > 1 else ""
if site:
    sys.path[0:0] = site.split(os.pathsep)

# LIBUNICORN_PATH: ctypes first-attempt location for libunicorn.so
# (importlib.resources cannot resolve the packaged path reliably on OHOS)
uc_lib = os.path.join(site, "unicorn", "lib") if site else ""
if uc_lib and os.path.isdir(uc_lib):
    os.environ["LIBUNICORN_PATH"] = uc_lib
    os.environ["LD_LIBRARY_PATH"] = uc_lib
    # Pre-load libunicorn.so (and .so.2) into the process so that unicorn's
    # own __load_uc_lib() reuses the same dlopen handle regardless of which
    # soname it resolves on the CI python (sys.platform linux vs ohos).
    import ctypes
    for _name in ("libunicorn.so", "libunicorn.so.2"):
        _p = os.path.join(uc_lib, _name)
        if os.path.isfile(_p):
            try:
                ctypes.cdll.LoadLibrary(_p)
                break
            except OSError:
                continue

import unicorn  # noqa: E402

mod_path = os.path.realpath(unicorn.__file__)
site_dirs = [os.path.realpath(s) for s in site.split(os.pathsep)] if site else []
if site_dirs and not any(mod_path.startswith(s) for s in site_dirs):
    raise AssertionError(f"unicorn imported from {mod_path}, not from package {site}")

# UC_VERSION_MAJOR / UC_VERSION_MINOR exist and version is sane
assert unicorn.UC_VERSION_MAJOR >= 2
assert unicorn.UC_VERSION_MINOR >= 0
print(unicorn.__name__)
print("uc_version:", unicorn.uc_version())
print("arm64 supported:", unicorn.uc_arch_supported(unicorn.UC_ARCH_ARM64))
assert unicorn.uc_arch_supported(unicorn.UC_ARCH_ARM64), "aarch64 not built in!"

# Run upstream regress unit test (arm64_reg_rw_w0_w30.py + regress.py framework)
regress_dir = sys.argv[2] if len(sys.argv) > 2 else ""
if regress_dir and os.path.isdir(regress_dir):
    test_file = os.path.join(regress_dir, "arm64_reg_rw_w0_w30.py")
    if os.path.isfile(test_file):
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [p for p in (site, regress_dir, env.get("PYTHONPATH", "")) if p])
        r = subprocess.run(
            [sys.executable, test_file], capture_output=True, text=True,
            env=env, timeout=120)
        if r.returncode != 0:
            sys.stderr.write(r.stdout + r.stderr)
            raise AssertionError(
                f"upstream regress test failed rc={r.returncode}")
        print("upstream regress arm64_reg_rw: OK")
