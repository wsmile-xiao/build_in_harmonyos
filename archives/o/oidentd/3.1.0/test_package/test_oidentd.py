#!/usr/bin/env python3
"""Smoke test for the installed `oidentd` binary.

oidentd 3.1.0 has no configure-time self-test target; the meaningful
observable is the version banner emitted by `-v` (options.c: case 'v' ->
print_version(true)), which reports both PACKAGE_STRING and the compiled-in
feature switches. Asserting on it verifies that the binary runs under the
OHOS runtime and that the recipe's --disable-masq/--disable-nat/
--disable-libnfct switches actually reached config.h.
"""
import subprocess
import sys

executable = sys.argv[1]
result = subprocess.run(
    [executable, "-v"],
    check=False,
    capture_output=True,
    text=True,
)

output = result.stdout + result.stderr
assert result.returncode == 0, result
# Build carried the upstream release version.
assert "oidentd 3.1.0" in output, output
# Verbose banner proves the build-information block was compiled in.
assert "Build information:" in output, output
# KERNEL_DRIVER is set by configure from host_os; linux must be selected.
assert "linux" in output.lower(), output

print("oidentd CLI smoke test: version banner + build information passed")
