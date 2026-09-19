#!/usr/bin/env python3
"""Consumer tests for the kernel-hardening-checker 0.6.17.1 Conan package.

Runs with the conanrun environment (PYTHONPATH set by package_info()):
  1. import kernel_hardening_checker and verify __version__
  2. upstream engine unit tests (14 cases, shipped inside the installed package)
  3. CLI wrapper: --version
  4. CLI wrapper: -p ARM64 (print hardening recommendations)
  5. CLI wrapper: -c <synthetic plain Kconfig file>
  6. CLI wrapper: -c <gzipped Kconfig file> (gzip code path)
  7. CLI wrapper: -c <shipped sample defconfig from config_files/>
  8. CLI error path: -c <nonexistent file>
"""
import gzip
import os
import shutil
import subprocess
import sys
import tempfile

import kernel_hardening_checker

EXPECTED_VERSION = "0.6.17.1"
FAILURES = []


def report(name, ok, detail=""):
    line = f"[{'PASS' if ok else 'FAIL'}] {name}"
    if detail:
        line += f" - {detail}"
    print(line)
    if not ok:
        FAILURES.append(name)


def run_cli(cli_path, args, timeout=90):
    return subprocess.run([cli_path] + args, capture_output=True, text=True, timeout=timeout)


def make_temp_dir():
    """First writable base wins: TMPDIR -> TMP -> system default -> ~/tmp."""
    candidates = [os.environ.get("TMPDIR"), os.environ.get("TMP"),
                  tempfile.gettempdir(), os.path.expanduser("~/tmp")]
    for base in candidates:
        if not base:
            continue
        try:
            os.makedirs(base, exist_ok=True)
            return tempfile.mkdtemp(prefix="khc-test-", dir=base)
        except OSError:
            continue
    raise RuntimeError("no writable temp directory found")


def main():
    # Test 1: import + version
    pkg_dir = os.path.dirname(kernel_hardening_checker.__file__)
    report("import kernel_hardening_checker", True, pkg_dir)
    report("__version__ matches", kernel_hardening_checker.__version__ == EXPECTED_VERSION,
           f"got {kernel_hardening_checker.__version__!r}")

    # Locate the CLI wrapper relative to the imported package
    # (.../lib/python3.X/site-packages/kernel_hardening_checker/__init__.py)
    pkg_root = os.path.abspath(os.path.join(pkg_dir, os.pardir, os.pardir, os.pardir, os.pardir))
    cli_path = os.path.join(pkg_root, "bin", "kernel-hardening-checker")
    report("CLI wrapper exists and is executable",
           os.path.isfile(cli_path) and os.access(cli_path, os.X_OK), cli_path)

    # Test 2: upstream engine unit tests (14 cases, official entrypoint
    # `python3 -m unittest -v -b` from the source root is equivalent to
    # running the test_engine module against the installed package)
    up = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "-b", "kernel_hardening_checker.test_engine"],
        capture_output=True, text=True, timeout=300)
    up_tail = ""
    for line in reversed((up.stderr or "").strip().splitlines()):
        if line.startswith(("Ran ", "OK", "FAILED")):
            up_tail = (up_tail + " " + line).strip()
    report("upstream unittest kernel_hardening_checker.test_engine (14 cases)",
           up.returncode == 0 and "OK" in (up.stderr or ""), (up_tail or f"rc={up.returncode}"))

    # Test 3: --version
    r = run_cli(cli_path, ["--version"])
    report("CLI --version",
           r.returncode == 0 and r.stdout.strip() == f"kernel-hardening-checker {EXPECTED_VERSION}",
           r.stdout.strip())

    # Test 4: -p ARM64
    r = run_cli(cli_path, ["-p", "ARM64"])
    report("CLI -p ARM64",
           r.returncode == 0
           and "Printing kernel security hardening options for ARM64" in r.stdout,
           f"rc={r.returncode}, {len(r.stdout)} bytes")

    # Synthetic Kconfig input for -c tests
    sample_config = (
        "# Linux/arm64 6.6.0 Kernel Configuration\n"
        "CONFIG_ARM64=y\n"
        "CONFIG_GCC_VERSION=1301\n"
        "CONFIG_CLANG_VERSION=0\n"
    )
    tmp = make_temp_dir()
    try:
        plain_cfg = os.path.join(tmp, "test.config")
        with open(plain_cfg, "w", encoding="utf-8") as f:
            f.write(sample_config)
        gz_cfg = os.path.join(tmp, "test.config.gz")
        with gzip.open(gz_cfg, "wb") as f:
            f.write(sample_config.encode("utf-8"))

        # Test 5: -c plain Kconfig
        r = run_cli(cli_path, ["-c", plain_cfg])
        report("CLI -c plain Kconfig",
               r.returncode == 0 and "Detected architecture: ARM64" in r.stdout
               and "Config check is finished" in r.stdout,
               f"rc={r.returncode}")

        # Test 6: -c gzipped Kconfig
        r = run_cli(cli_path, ["-c", gz_cfg])
        report("CLI -c gzipped Kconfig",
               r.returncode == 0 and "Detected architecture: ARM64" in r.stdout
               and "Config check is finished" in r.stdout,
               f"rc={r.returncode}")

        # Test 7: shipped sample defconfig from config_files/
        shipped = os.path.join(pkg_dir, "config_files", "defconfigs",
                               "arm64_defconfig_6.6.config")
        report("shipped config_files sample present", os.path.isfile(shipped), shipped)
        if os.path.isfile(shipped):
            r = run_cli(cli_path, ["-c", shipped], timeout=180)
            report("CLI -c shipped arm64_defconfig_6.6.config",
                   r.returncode == 0 and "Detected architecture: ARM64" in r.stdout,
                   f"rc={r.returncode}")

        # Test 8: error path (mirrors upstream functional_test.sh error checks)
        r = run_cli(cli_path, ["-c", os.path.join(tmp, "missing.config")])
        report("CLI -c missing file exits nonzero with ERROR",
               r.returncode != 0 and "ERROR" in (r.stderr + r.stdout),
               f"rc={r.returncode}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print(f"=== {len(FAILURES)} consumer test(s) FAILED: {FAILURES} ===")
        return 1
    print("=== All consumer tests passed ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
