#!/bin/bash
# test_package/test.sh — xf86-video-r128 driver module test
# Verifies that the r128_drv.so driver module exists in the package at the
# declared install path, is a valid ELF64 shared object and exports the
# module entry point. The module is loaded at runtime by the X server, so
# link/run tests against it are not applicable.

set -euo pipefail

# Get package root from the first argument
PKG_ROOT="${1:-}"

if [ -z "$PKG_ROOT" ]; then
    echo "FAIL: package root not provided"
    exit 1
fi

# The conanfile declares libdirs = ["lib/xorg/modules/drivers"], so the
# consumer-facing layout assertion uses exactly that path.
DRIVER="$PKG_ROOT/lib/xorg/modules/drivers/r128_drv.so"

echo "[test] looking for r128_drv.so in $PKG_ROOT"
if [ ! -f "$DRIVER" ]; then
    echo "FAIL: r128_drv.so not found at lib/xorg/modules/drivers/"
    exit 1
fi
echo "OK: found driver module at $DRIVER"

# Validate the ELF header and the exported dynamic symbol table with
# python3, which is guaranteed on the CI worker (conan runs on it).
python3 - "$DRIVER" <<'PYEOF'
import struct
import sys

path = sys.argv[1]
with open(path, "rb") as fh:
    blob = fh.read()

# --- ELF header ---
if blob[:4] != b"\x7fELF":
    print("FAIL: not an ELF file")
    sys.exit(1)
if blob[4] != 2:
    print("FAIL: not a 64-bit ELF")
    sys.exit(1)
e_type = struct.unpack_from("<H", blob, 16)[0]
if e_type != 3:  # ET_DYN — shared object
    print(f"FAIL: not a shared object (e_type={e_type})")
    sys.exit(1)
print("OK: valid ELF64 shared object (ET_DYN)")

# --- dynamic symbol table ---
e_shoff = struct.unpack_from("<Q", blob, 0x28)[0]
e_shentsize = struct.unpack_from("<H", blob, 0x3A)[0]
e_shnum = struct.unpack_from("<H", blob, 0x3C)[0]
e_shstrndx = struct.unpack_from("<H", blob, 0x3E)[0]


def section(idx):
    off = e_shoff + idx * e_shentsize
    (name, _typ, _flags, _addr, offset, size, _link, _info,
     _align, _entsize) = struct.unpack_from("<IIQQQQIIQQ", blob, off)
    return name, offset, size


if e_shoff == 0 or e_shnum == 0:
    print("FAIL: no section header table (stripped?)")
    sys.exit(1)

_, shstr_off, shstr_size = section(e_shstrndx)
shstrtab = blob[shstr_off:shstr_off + shstr_size]

dynstr = None
for i in range(e_shnum):
    name_off, off, size = section(i)
    end = shstrtab.find(b"\x00", name_off)
    name = shstrtab[name_off:end].decode("ascii", "replace")
    if name == ".dynstr":
        dynstr = blob[off:off + size]
        break

if dynstr is None:
    print("FAIL: no .dynstr section")
    sys.exit(1)

# Only names present in the dynamic string table count as exported;
# r128ModuleData is the module entry (_X_EXPORT in src/r128_misc.c).
needle = b"r128ModuleData\x00"
if needle not in dynstr:
    print("FAIL: r128ModuleData not exported in .dynstr")
    sys.exit(1)
print("OK: r128ModuleData entry point exported")
PYEOF

echo "All tests passed."
