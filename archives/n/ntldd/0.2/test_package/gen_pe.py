#!/usr/bin/env python3
"""Generate a tiny valid PE32 executable for exercising ntldd.

The file imports two DLLs (KERNEL32.dll and advapi32.dll) through a minimal
import table, which is exactly the part of the PE format ntldd walks. The
layout keeps every RVA equal to its raw file offset plus 0x400 so the file
can also be inspected with llvm-objdump / dumpbin as ground truth.
"""

import struct
import sys

DOS_HEADER = struct.pack(
    "<64s",
    b"\x4d\x5a" + b"\x00" * 58 + struct.pack("<I", 0x80),
)

FILE_HEADER = struct.pack(
    "<HHIIIHH",
    0x014C,  # Machine: i386
    1,  # NumberOfSections
    0,  # TimeDateStamp
    0,  # PointerToSymbolTable
    0,  # NumberOfSymbols
    224,  # SizeOfOptionalHeader
    0x0102,  # Characteristics: EXECUTABLE_IMAGE | 32BIT_MACHINE
)


def optional_header(import_rva, import_size):
    fields = struct.pack(
        "<HBB9I6H4I2H6I",
        0x010B,  # Magic PE32
        1, 0,  # linker version
        0x200,  # SizeOfCode
        0, 0,  # SizeOfInitialized/UninitializedData
        0,  # AddressOfEntryPoint
        0x1000,  # BaseOfCode
        0x1000,  # BaseOfData
        0x400000,  # ImageBase
        0x1000,  # SectionAlignment
        0x200,  # FileAlignment
        4, 0, 0, 0, 4, 0,  # OS/image/subsystem versions
        0,  # Win32VersionValue
        0x600,  # SizeOfImage
        0x400,  # SizeOfHeaders
        0,  # CheckSum
        3,  # Subsystem: console
        0,  # DllCharacteristics
        0x100000, 0x1000, 0x100000, 0x1000,  # stack/heap
        0,  # LoaderFlags
        16,  # NumberOfRvaAndSizes
    )
    assert len(fields) == 96, len(fields)
    directories = b"\x00" * 8 * 16
    directories = (
        directories[: 1 * 8]
        + struct.pack("<II", import_rva, import_size)
        + directories[2 * 8 :]
    )
    return fields + directories


SECTION_HEADER = struct.pack(
    "<8sIIIIIIHHI",
    b".idata",
    0x200,  # VirtualSize
    0x400,  # VirtualAddress
    0x200,  # SizeOfRawData
    0x400,  # PointerToRawData
    0, 0, 0, 0,
    0xC0000040,  # MEM_READ | MEM_WRITE | INITIALIZED_DATA
)


def idata():
    # RVA (== file offset) plan inside .idata (base 0x400):
    #   0x400 descriptor[0] (KERNEL32.dll)
    #   0x414 descriptor[1] (advapi32.dll)
    #   0x428 terminator descriptor
    #   0x43C INT[0]: -> 0x480, 0
    #   0x444 IAT[0]: -> 0x480, 0
    #   0x44C INT[1]: -> 0x4A0, 0
    #   0x454 IAT[1]: -> 0x4A0, 0
    #   0x45C "KERNEL32.dll\0"
    #   0x46A "advapi32.dll\0"
    #   0x480 hint/name "Foo"
    #   0x4A0 hint/name "Bar"
    blob = bytearray(0x200)

    def put(offset, data):
        blob[offset - 0x400 : offset - 0x400 + len(data)] = data

    put(0x400, struct.pack("<IIIII", 0x43C, 0, 0, 0x45C, 0x444))
    put(0x414, struct.pack("<IIIII", 0x44C, 0, 0, 0x46A, 0x454))
    put(0x428, b"\x00" * 20)
    put(0x43C, struct.pack("<II", 0x480, 0))
    put(0x444, struct.pack("<II", 0x480, 0))
    put(0x44C, struct.pack("<II", 0x4A0, 0))
    put(0x454, struct.pack("<II", 0x4A0, 0))
    put(0x45C, b"KERNEL32.dll\x00")
    put(0x46A, b"advapi32.dll\x00")
    put(0x480, struct.pack("<H", 0) + b"Foo\x00")
    put(0x4A0, struct.pack("<H", 0) + b"Bar\x00")
    return bytes(blob)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "tiny.exe"
    header = DOS_HEADER + b"\x00" * 0x40 + b"PE\x00\x00" + FILE_HEADER
    header += optional_header(0x400, 3 * 20 + 0x40) + SECTION_HEADER
    header += b"\x00" * (0x400 - len(header))
    with open(out, "wb") as f:
        f.write(header + idata())
    print(f"wrote {out} ({0x600} bytes)")


if __name__ == "__main__":
    main()
