#!/usr/bin/env python3
"""Conan test_package for tkpng — R34 real artifact verification (no empty shell).

tkpng ships lib/tkpng0.9.so (Tcl/Tk PNG image-format extension). The OHOS
sandbox cannot run tclsh9.0 (libtcl9.0.so relocation error — the tcl package's
own runtime issue, E212-class dlopen restriction), so the strongest check
available without a Tcl interpreter is:
  1. the .so exists under <pkg>/lib/,
  2. it is a valid ELF shared object (ET_DYN),
  3. it contains the tkpng PNG registration symbols (tkImgFmtPNG) — proving
     the PNG format code was compiled in.

Note: this is a static artifact check (ELF magic + symbol-string search), not
a DT_NEEDED/dynamic-section parse — the .so links TEA stub libs statically
(libtclstub.a/libtkstub.a) so no runtime library dependency is expected.
"""
import os
import struct
import sys


ELF_MAGIC = b"\x7fELF"


def _is_elf_shared_object(path):
    """Return True if path is an ELF shared object (magic + ET_DYN)."""
    with open(path, "rb") as f:
        ident = f.read(16)
    if len(ident) < 16 or ident[:4] != ELF_MAGIC:
        return False
    with open(path, "rb") as f:
        f.seek(16)
        e_type_raw = f.read(2)
    if len(e_type_raw) < 2:
        return False
    e_type = struct.unpack("<H", e_type_raw)[0]
    return e_type == 3  # ET_DYN


def main():
    pkg = sys.argv[1]
    so = os.path.join(pkg, "lib", "libtkpng0.9.so")
    if not os.path.isfile(so):
        print(f"FAIL: {so} not found", file=sys.stderr)
        return 1

    # R34: confirm the .so is a valid ELF shared object.
    if not _is_elf_shared_object(so):
        print("FAIL: libtkpng0.9.so is not an ELF shared object", file=sys.stderr)
        return 1

    # Verify it exports the tkpng PNG registration symbol (TEA 用静态
    # libtclstub.a/libtkstub.a 链接，符号并入 .so——校验导出的
    # tkImgFmtPNG 符号串证明扩展已编译且含 PNG 格式注册代码）。
    with open(so, "rb") as f:
        blob = f.read()
    if b"tkImgFmtPNG" not in blob:
        print("FAIL: libtkpng0.9.so does not export tkImgFmtPNG", file=sys.stderr)
        return 1

    print(f"OK: tkpng {os.path.basename(so)} present + valid ELF + exports tkImgFmtPNG")
    return 0


if __name__ == "__main__":
    sys.exit(main())
