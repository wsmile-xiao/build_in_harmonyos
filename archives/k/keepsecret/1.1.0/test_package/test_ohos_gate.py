#!/usr/bin/env python3
"""OHOS adaptation gate test for the packaged keepsecret 1.1.0.

New OHOS-specific test (build_in_harmonyos port, not an upstream case): it
asserts, directly on the packaged ELF, that the platform adaptations this port
introduces actually took effect in the shipped artifact:

  1. The binary is an AArch64 ELF for the OHOS target.
  2. KF6::I18nQml is not linked (patches 0001/0002 replaced KLocalizedQmlContext
     with KLocalizedContext from libKF6I18n.so.6).
  3. The QML application closure is linked (libQt6Qml/libQt6Quick) and the
     libsecret-1 secret-store backend survived linking (pkg_check_modules
     LIBSECRET in the top-level CMakeLists).

Note: the org.kde.coreaddons / org.kde.config / org.kde.kitemmodels QML module
imports rewritten by patches 0003/0004/0005 are QML runtime imports, not
DT_NEEDED entries, so their absence is NOT asserted here - it is covered by the
offscreen launch smoke, which loads Main.qml and would fail if those imports
were still present.

Pure stdlib: a minimal ELF64 parser extracts the PT_DYNAMIC DT_NEEDED strings,
so the gate does not depend on readelf being on the CI PATH (kio 6.14.0
precedent: readelf can be absent).

Usage: test_ohos_gate.py <path-to-packaged-keepsecret-binary>
Exit code 0 = gate passed, 1 = gate failed.
"""
import struct
import sys

DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10
PT_LOAD = 1
PT_DYNAMIC = 2
EM_AARCH64 = 183

DENY_SUBSTRINGS = ("I18nQml",)
# DT_NEEDED entries may be bare sonames ("libQt6Core.so.6") or absolute paths
# recorded at build time ("/.../p/lib/libKF6I18n.so"), so match on the library
# base name without the version suffix.
REQUIRED_NEEDED = (
    "libQt6Core.so",
    "libQt6Qml.so",
    "libQt6Quick.so",
    "libKF6I18n.so",
    "libsecret-1.so",
    "libc.so",
)


class GateError(Exception):
    pass


def parse_elf_needed(data):
    if data[:4] != b"\x7fELF":
        raise GateError("not an ELF file")
    if data[4] != 2:
        raise GateError("expected ELFCLASS64")
    if data[5] != 1:
        raise GateError("expected little-endian ELF")

    e_type, e_machine = struct.unpack_from("<HH", data, 0x10)
    (e_phoff,) = struct.unpack_from("<Q", data, 0x20)
    e_phentsize, e_phnum = struct.unpack_from("<HH", data, 0x36)
    if e_machine != EM_AARCH64:
        raise GateError(f"expected EM_AARCH64 (183), got {e_machine}")

    dynamic = None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, = struct.unpack_from("<I", data, off)
        if p_type == PT_DYNAMIC:
            p_offset, p_vaddr = struct.unpack_from("<QQ", data, off + 8)
            p_filesz, = struct.unpack_from("<Q", data, off + 32)
            dynamic = (p_offset, p_vaddr, p_filesz)
            break
    if dynamic is None:
        raise GateError("no PT_DYNAMIC segment found")

    p_offset, p_vaddr, p_filesz = dynamic
    # Resolve dynamic entries to file offsets through the PT_LOAD mapping.
    loads = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, = struct.unpack_from("<I", data, off)
        if p_type != PT_LOAD:
            continue
        # Elf64_Phdr: p_type(4) p_flags(4) p_offset(8) p_vaddr(8) p_paddr(8)
        #              p_filesz(8) p_memsz(8) p_align(8)
        load_offset, = struct.unpack_from("<Q", data, off + 8)
        load_vaddr, = struct.unpack_from("<Q", data, off + 16)
        load_filesz, = struct.unpack_from("<Q", data, off + 32)
        loads.append((load_vaddr, load_filesz, load_offset))

    def vaddr_to_off(addr):
        for vaddr, filesz, offset in loads:
            if vaddr <= addr < vaddr + filesz:
                return offset + (addr - vaddr)
        return None

    entries = []
    for pos in range(p_offset, p_offset + p_filesz, 16):
        d_tag, d_val = struct.unpack_from("<qQ", data, pos)
        if d_tag == 0:
            break
        entries.append((d_tag, d_val))

    strtab_off = None
    strsz = None
    needed_offsets = []
    for d_tag, d_val in entries:
        if d_tag == DT_NEEDED:
            needed_offsets.append(d_val)
        elif d_tag == DT_STRTAB:
            strtab_off = vaddr_to_off(d_val)
        elif d_tag == DT_STRSZ:
            strsz = d_val
    if strtab_off is None:
        raise GateError("no DT_STRTAB found")

    names = []
    for name_off in needed_offsets:
        start = strtab_off + name_off
        end = data.find(b"\x00", start)
        if end == -1:
            raise GateError("unterminated DT_NEEDED string")
        names.append(data[start:end].decode("utf-8", "replace"))
    return names


def main():
    if len(sys.argv) != 2:
        print("usage: test_ohos_gate.py <path-to-binary>", file=sys.stderr)
        return 2
    binary = sys.argv[1]
    with open(binary, "rb") as handle:
        data = handle.read()

    needed = parse_elf_needed(data)
    print("DT_NEEDED entries: %d" % len(needed))

    failures = []
    for name in needed:
        for denied in DENY_SUBSTRINGS:
            if denied in name:
                failures.append(f"unexpected dependency on {name} (deny {denied!r})")
    for required in REQUIRED_NEEDED:
        if not any(required in name for name in needed):
            failures.append(f"missing required dependency {required}")

    if failures:
        for item in failures:
            print("GATE-FAIL: %s" % item, file=sys.stderr)
        return 1

    print("GATE-PASS: OHOS aarch64 ELF, no unpublished I18nQml dependency, "
          "QML + libsecret-1 closure linked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
