#!/usr/bin/env python3
"""ELF target assertions for the packaged yaku-ns commands (3 assertions).

Reads the ELF header of both delivered binaries directly (no external tooling, so
this works on the OHOS worker as well as on a Linux host) and checks:

  1. yaku-ns is ELFCLASS64
  2. yaku-getzone is ELFCLASS64
  3. both carry the e_machine of the requested target architecture and are
     little-endian

The expected machine is passed in by the caller from ``settings.arch`` rather
than hard-coded, so the recipe's promise (``validate()`` accepts Linux and OHOS)
is actually honoured on a non-aarch64 host instead of failing on a mismatch
between what the recipe accepts and what the test demands.  The OHOS CI profile
pins ``arch=armv8``, which maps to EM_AARCH64.
"""

import struct
import sys

# e_machine values for the architectures this recipe can be built for.
E_MACHINE = {
    "armv8": (183, "EM_AARCH64"),
    "x86_64": (62, "EM_X86_64"),
    "armv7": (40, "EM_ARM"),
    "x86": (3, "EM_386"),
}

ELFCLASS64 = 2
ELFDATA2LSB = 1

ASSERTIONS = 3


def read_elf_header(path):
    with open(path, "rb") as fh:
        head = fh.read(20)
    if len(head) < 20 or head[:4] != b"\x7fELF":
        raise ValueError("%s is not an ELF file" % path)
    ei_class, ei_data = head[4], head[5]
    e_machine = struct.unpack_from("<H", head, 18)[0]
    return ei_class, ei_data, e_machine


def check(index, description, condition, detail=""):
    if condition:
        print("PASS [%d/%d] %s" % (index, ASSERTIONS, description))
        return 0
    print("FAIL [%d/%d] %s" % (index, ASSERTIONS, description))
    if detail:
        print(detail)
    return 1


def main():
    daemon, getzone = sys.argv[1], sys.argv[2]
    conan_arch = sys.argv[3] if len(sys.argv) > 3 else "armv8"
    if conan_arch not in E_MACHINE:
        print("test_elf_abi: unsupported target arch %r (known: %s)"
              % (conan_arch, ", ".join(sorted(E_MACHINE))))
        return 1
    expected_machine, machine_name = E_MACHINE[conan_arch]

    failures = 0
    headers = {}
    for label, path in (("yaku-ns", daemon), ("yaku-getzone", getzone)):
        try:
            headers[label] = read_elf_header(path)
        except ValueError as exc:
            headers[label] = None
            print("FAIL %s header unreadable: %s" % (label, exc))

    daemon_header = headers.get("yaku-ns")
    getzone_header = headers.get("yaku-getzone")

    failures += check(1, "yaku-ns is a 64-bit ELF",
                      daemon_header is not None
                      and daemon_header[0] == ELFCLASS64,
                      "EI_CLASS=%r" % (daemon_header[0] if daemon_header else None,))
    failures += check(2, "yaku-getzone is a 64-bit ELF",
                      getzone_header is not None
                      and getzone_header[0] == ELFCLASS64,
                      "EI_CLASS=%r"
                      % (getzone_header[0] if getzone_header else None,))

    details = []
    matched = True
    for label in ("yaku-ns", "yaku-getzone"):
        header = headers.get(label)
        if header is None:
            matched = False
            details.append("%s: header unreadable" % label)
            continue
        _cls, data, machine = header
        if machine != expected_machine or data != ELFDATA2LSB:
            matched = False
            details.append("%s: e_machine=%d EI_DATA=%d" % (label, machine, data))
    failures += check(3, "both binaries are little-endian %s"
                      % machine_name,
                      matched, "; ".join(details))

    if failures:
        print("test_elf_abi: %d/%d assertions FAILED" % (failures, ASSERTIONS))
        return 1
    print("test_elf_abi: %d/%d assertions passed" % (ASSERTIONS, ASSERTIONS))
    return 0


if __name__ == "__main__":
    sys.exit(main())