#!/usr/bin/env python3
"""Generate a minimal but well-formed PE32 image for the pev smoke test.

This is the test source of test_package/ (CI L0c: `.py` under test_package/,
tracked in git). test_package/conanfile.py's test() executes it at test time
to produce the sample that `readpe` / `pehash` then parse.

The image layout:
DOS header + stub, 'PE\\0\\0' + COFF + PE32 optional header, three
section headers (.text/.data/.rsrc). The resource section carries a
minimal 3-level directory (type 16 → id 1 → lang 0x409) so peres has a
valid resource tree to walk.

usage: pe32_sample.py <output-path>
"""

import struct
import sys


def write_minimal_pe32(path):
    """Emit a tiny but valid PE32 image for the toolkit to parse."""
    dos = struct.pack(
        "<2s13H4H2H10HI",
        b"MZ", 0x90, 3, 0, 4, 0, 0xFFFF, 0, 0xB8, 0, 0, 0, 0x40, 0,
        0, 0, 0, 0,
        0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0x80,
    )
    stub = b"This program cannot be run in DOS mode.\r\r\n$"
    dos += stub + b"\x00" * (0x80 - len(dos) - len(stub))

    image = dos + b"PE\x00\x00"
    image += struct.pack(
        "<HHIIIHH",
        0x014C, 3, 0, 0, 0, 0xE0, 0x0102,
    )
    dirs = [(0, 0)] * 16
    dirs[2] = (0x3000, 0x98)  # resource directory
    opt = [0x10B, 1, 0]
    opt += [0x200, 0x600, 0, 0x1000, 0x1000, 0x2000]        # sizes/entry/bases
    opt += [0x400000, 0x1000, 0x200]                        # image/section/file align
    opt += [4, 0, 0, 0, 4, 0]                               # OS/image/subsystem versions
    opt += [0, 0x4000, 0x400, 0]                            # win32ver, sizeofimage, hdrs, cksum
    opt += [3, 0]                                           # subsystem console, dllchars
    opt += [0x100000, 0x1000, 0x100000, 0x1000, 0, 16]      # stacks/heaps, loaderflags, ndirs
    image += struct.pack("<HBB9I6H4I2H6I", *opt)
    for rva, size in dirs:
        image += struct.pack("<II", rva, size)

    def section(name, vsize, va, rawsize, rawptr, chars):
        return struct.pack(
            "<8s6I2HI", name, vsize, va, rawsize, rawptr, 0, 0, 0, 0, chars
        )

    image += section(b".text\x00\x00\x00", 0x10, 0x1000, 0x200, 0x400, 0x60000020)
    image += section(b".data\x00\x00\x00", 0x10, 0x2000, 0x200, 0x600, 0xC0000040)
    image += section(b".rsrc\x00\x00\x00", 0x98, 0x3000, 0x200, 0x800, 0x40000040)
    image += b"\x00" * (0x400 - len(image))

    text = b"\xC3" + b"\x00" * 0x1F                          # ret; padded
    data = b"pev-smoke-test\x00" + b"\x00" * 0x10
    rsrc = struct.pack("<IIHHHH", 0, 0, 0, 0, 0, 1)          # root @0x00
    rsrc += struct.pack("<II", 16, 0x80000000 | 0x28)        # type entry @0x10
    rsrc += b"\x00" * 0x10                                   # pad to 0x28
    rsrc += struct.pack("<IIHHHH", 0, 0, 0, 0, 0, 1)         # level-2 dir @0x28
    rsrc += struct.pack("<II", 1, 0x80000000 | 0x50)         # name entry @0x38
    rsrc += b"\x00" * 0x10                                   # pad to 0x50
    rsrc += struct.pack("<IIHHHH", 0, 0, 0, 0, 0, 1)         # level-3 dir @0x50
    rsrc += struct.pack("<II", 0x409, 0x78)                  # lang entry @0x68
    rsrc += b"\x00" * 0x10                                   # pad to 0x78
    rsrc += struct.pack("<IIII", 0x3088, 0x10, 0, 0)         # data entry @0x78
    rsrc += b"pev-resource\x00\x00\x00\x00"                  # data blob @0x88
    assert len(rsrc) == 0x98

    image += text + b"\x00" * (0x200 - len(text))
    image += data + b"\x00" * (0x200 - len(data))
    image += rsrc + b"\x00" * (0x200 - len(rsrc))
    assert len(image) == 0xA00

    with open(path, "wb") as f:
        f.write(image)


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: pe32_sample.py <output-path>\n")
        return 2
    write_minimal_pe32(argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
