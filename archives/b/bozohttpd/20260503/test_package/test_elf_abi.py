#!/usr/bin/env python3
"""Check that the cross-built server is an AArch64 ELF executable."""

import sys


def main(path):
    with open(path, "rb") as executable:
        header = executable.read(20)
    assert header[:4] == b"\x7fELF", "package binary is not ELF"
    assert header[4] == 2, f"expected ELF64, got class {header[4]}"
    assert header[5] in (1, 2), f"unsupported ELF byte order {header[5]}"
    byteorder = "little" if header[5] == 1 else "big"
    machine = int.from_bytes(header[18:20], byteorder)
    assert machine == 183, f"expected AArch64 e_machine=183, got {machine}"


if __name__ == "__main__":
    main(sys.argv[1])
