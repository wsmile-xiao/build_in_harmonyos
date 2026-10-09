#!/usr/bin/env python3
"""Generate a minimal but valid Windows NT registry hive for testing winregfs.

Upstream winregfs ships no test fixtures and no automated test suite; its two
real entry points are `fsck.winregfs <hive>` (traverse a hive and report
errors) and `mount.winregfs <hive> <mnt>` (FUSE mount). This generator emits a
small, structurally valid hive so those entry points can be exercised for real:

    \\ROOT
      Version  REG_DWORD = 0x123
      \\Test
        Path   REG_SZ    = "OHOS"
        Count  REG_DWORD = 7

The byte layout follows the structs in ntreg.h (regf header page, one hbin
page, 8-byte aligned cells, cell offsets relative to 0x1000 at the cell start).
"""
import struct
import sys

HBIN = 0x1000
CELL = 0x1000  # first hbin starts after the 4096-byte regf header page


def cell(size, payload):
    """A hive cell: 4-byte signed size (negative == allocated) + payload."""
    assert size % 8 == 0 and size >= len(payload) + 4
    return struct.pack("<i", -size) + payload + b"\x00" * (size - 4 - len(payload))


def nk(name, ktype, ofs_parent, no_subkeys, ofs_lf, no_values, ofs_vallist, size):
    b = bytearray(0x4C)
    struct.pack_into("<hh", b, 0x00, 0x6B6E, ktype)          # "nk"
    struct.pack_into("<I", b, 0x10, ofs_parent)
    struct.pack_into("<i", b, 0x14, no_subkeys)
    struct.pack_into("<I", b, 0x1C, ofs_lf)
    struct.pack_into("<i", b, 0x24, no_values)
    struct.pack_into("<i", b, 0x28, ofs_vallist)
    struct.pack_into("<I", b, 0x2C, 0xFFFFFFFF)              # no sk
    struct.pack_into("<I", b, 0x30, 0xFFFFFFFF)              # no class name
    struct.pack_into("<h", b, 0x48, len(name))
    b += name.encode()
    return cell(size, bytes(b))


def vk(name, val_type, data_cell_ofs, inline_dword=None):
    b = bytearray(0x14)
    struct.pack_into("<h", b, 0x00, 0x6B76)                  # "vk"
    struct.pack_into("<h", b, 0x02, len(name))
    if inline_dword is None:
        struct.pack_into("<I", b, 0x04, data_cell_ofs[1])    # length of data
        struct.pack_into("<i", b, 0x08, data_cell_ofs[0])    # offset of data cell
    else:
        struct.pack_into("<I", b, 0x04, 4 | 0x80000000)      # inline
        struct.pack_into("<i", b, 0x08, inline_dword)
    struct.pack_into("<i", b, 0x0C, val_type)
    struct.pack_into("<h", b, 0x10, 1)                       # flag: ASCII name
    b += name.encode()
    return cell(0x20, bytes(b))


def build():
    # --- layout (offsets are cell starts, relative to the first regf page) ---
    at_root = 0x20
    at_lf = 0x78
    at_sub = 0x88
    at_root_vlist = 0xE0
    at_root_vk = 0xE8
    at_sub_vlist = 0x108
    at_path_vk = 0x118
    at_count_vk = 0x138
    at_path_data = 0x158
    at_free = 0x170

    page = bytearray(HBIN)
    struct.pack_into("<4sii", page, 0x00, b"hbin", 0, HBIN)
    # struct hbin_page has 2 bytes of padding before len_page; data starts at 0x20.

    def put(ofs, blob):
        page[ofs:ofs + len(blob)] = blob

    put(at_root, nk("ROOT", 0x2C, 0xFFFFFFFF, 1, at_lf, 1, at_root_vlist, 0x58))

    # lf index: one entry -> subkey "Test"
    put(at_lf, cell(0x10, struct.pack("<hh", 0x666C, 1) + struct.pack("<i", at_sub) + b"Test"))
    put(at_sub, nk("Test", 0x20, at_root, 0, 0xFFFFFFFF, 2, at_sub_vlist, 0x58))
    put(at_root_vlist, cell(0x08, struct.pack("<i", at_root_vk)))
    put(at_root_vk, vk("Version", 4, None, inline_dword=0x123))
    put(at_sub_vlist, cell(0x10, struct.pack("<ii", at_path_vk, at_count_vk)))
    put(at_path_vk, vk("Path", 1, (at_path_data, 10)))
    put(at_count_vk, vk("Count", 4, None, inline_dword=7))
    put(at_path_data, cell(0x18, "OHOS\x00".encode("utf-16-le")))
    # trailing free cell fills the hbin exactly (positive size == free)
    page[at_free:HBIN] = struct.pack("<i", HBIN - at_free) + b"\x00" * (HBIN - at_free - 4)

    # --- regf header page ---
    hdr = bytearray(CELL)
    struct.pack_into("<4s", hdr, 0x00, b"regf")
    struct.pack_into("<ii", hdr, 0x04, 1, 1)          # sequence numbers
    struct.pack_into("<i", hdr, 0x14, 1)              # major version
    struct.pack_into("<i", hdr, 0x18, 3)              # minor version
    struct.pack_into("<i", hdr, 0x20, 1)              # file format
    struct.pack_into("<i", hdr, 0x24, at_root)        # root cell offset
    struct.pack_into("<i", hdr, 0x28, HBIN)           # hbin data size
    struct.pack_into("<i", hdr, 0x2C, 1)
    hdr[0x30:0x30 + 4] = b"ROOT"
    chk = 0
    for off in range(0, 0x1FC, 4):
        chk ^= struct.unpack_from("<I", hdr, off)[0]
    struct.pack_into("<I", hdr, 0x1FC, chk)

    return bytes(hdr) + bytes(page)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "minimal.hiv"
    data = build()
    with open(out, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes, %d pages)" % (out, len(data), len(data) // 0x1000))


if __name__ == "__main__":
    main()
