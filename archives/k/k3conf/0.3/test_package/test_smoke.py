#!/usr/bin/env python3
import struct
import subprocess
import sys


def run(binary, option):
    return subprocess.run(
        [binary, option], check=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True,
    ).stdout


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_smoke.py /path/to/k3conf <Conan OS>")
    binary, target_os = sys.argv[1:]

    help_text = run(binary, "--help")
    if "k3conf - TI K3 Configuration Diagnostic Tool" not in help_text:
        raise SystemExit("--help output did not identify k3conf")
    if "COMMANDS" not in help_text or "k3conf show hosts" not in help_text:
        raise SystemExit("--help output omitted the command reference")
    print("PASS: --help reports k3conf usage and commands")

    version_text = run(binary, "--version")
    if "K3CONF" not in version_text or "v0.3" not in version_text:
        raise SystemExit("--version output did not contain upstream version v0.3")
    print("PASS: --version reports upstream version v0.3")

    if target_os == "OHOS":
        with open(binary, "rb") as executable:
            header = executable.read(20)
        if len(header) != 20 or header[:4] != b"\x7fELF":
            raise SystemExit("HarmonyOS package is not an ELF executable")
        if header[4] != 2 or header[5] != 1:
            raise SystemExit("HarmonyOS package is not a 64-bit little-endian ELF")
        if struct.unpack_from("<H", header, 18)[0] != 183:
            raise SystemExit("HarmonyOS package ELF machine is not AArch64")
        print("PASS: HarmonyOS package is a 64-bit little-endian AArch64 ELF")


if __name__ == "__main__":
    main()
