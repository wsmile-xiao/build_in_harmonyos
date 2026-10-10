#!/usr/bin/env python3
"""Consumer smoke checks; never starts the syslog daemon or touches /dev/log."""

import os
import struct
import subprocess
import sys
import tempfile


def run_cli(binary, *args):
    return subprocess.run(
        [binary, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=15, check=False,
    )


def check_elf64_aarch64(path):
    with open(path, "rb") as stream:
        header = stream.read(20)
    assert len(header) == 20 and header[:4] == b"\x7fELF", "invalid ELF header"
    assert header[4] == 2, "expected ELF64 package executable"
    byte_order = {1: "<", 2: ">"}.get(header[5])
    assert byte_order is not None, "invalid ELF byte order"
    machine = struct.unpack(byte_order + "H", header[18:20])[0]
    assert machine == 183, "expected AArch64 ELF machine 183, got {}".format(machine)


def main():
    binary = os.path.abspath(sys.argv[1])
    target_os = sys.argv[2]
    runtime_available = sys.argv[3] == "1"
    checks = 0

    # The architecture assertion is mandatory for HarmonyOS AArch64 packages.
    if target_os == "OHOS":
        check_elf64_aarch64(binary)
        checks += 1
        print("PASS HarmonyOS ELF64 AArch64 ABI (e_machine=183)")

    if not runtime_available:
        print("SKIP 4 CLI/config checks: Conan reports target executable cannot run here")
        print("PASS total assertions: {} (4 runtime checks skipped)".format(checks))
        return

    version = run_cli(binary, "--version")
    if version.returncode != 0 or "metalog version" not in version.stdout:
        raise AssertionError("--version failed: {}".format(version.stderr.strip()))
    checks += 1
    print("PASS --version")

    help_result = run_cli(binary, "--help")
    if help_result.returncode != 0 or "--test-config" not in help_result.stdout:
        raise AssertionError("--help did not document --test-config")
    checks += 1
    print("PASS --help")

    with tempfile.TemporaryDirectory(prefix="metalog-test-") as temp_dir:
        valid_path = os.path.join(temp_dir, "valid.conf")
        invalid_path = os.path.join(temp_dir, "invalid.conf")
        with open(valid_path, "w", encoding="utf-8") as config:
            config.write('Test section:\n  facility = "*"\n  logdir = "{}"\n'.format(temp_dir))
        with open(invalid_path, "w", encoding="utf-8") as config:
            config.write("Test section:\n  unknown_directive = bad\n")

        valid = run_cli(binary, "--test-config", "--no-kernel", "--configfile", valid_path)
        if valid.returncode != 0:
            raise AssertionError("valid config rejected: {}".format(valid.stderr.strip()))
        checks += 1
        print("PASS valid configuration parse")

        invalid = run_cli(binary, "--test-config", "--no-kernel", "--configfile", invalid_path)
        if invalid.returncode == 0:
            raise AssertionError("invalid config was accepted")
        checks += 1
        print("PASS invalid configuration rejected")

    print("PASS total assertions: {}".format(checks))


if __name__ == "__main__":
    main()
