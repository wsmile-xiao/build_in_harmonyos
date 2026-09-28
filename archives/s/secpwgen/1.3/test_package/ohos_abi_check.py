#!/usr/bin/env python3
"""HarmonyOS artifact/ABI checks for secpwgen 1.3 (pure Python, no external tools).

These are the HarmonyOS-specific test cases that can be evaluated on *any*
build host, because they inspect the cross-compiled artifact instead of
executing it (an aarch64-linux-ohos ELF cannot run on the macOS dev box that
simulates the OHOS worker, and `can_run()` is False there).  They are invoked
twice: from the recipe's build() (with --object, so the E051 guard check runs
too) and from test_package/conanfile.py test() (packaged binary only).

Checks
  A1  ELF64 + e_machine == EM_AARCH64      HarmonyOS PC arm64 target
  A2  .interp == /lib/ld-musl-aarch64.so.1 OHOS musl loader (glibc would be
                                           /lib/ld-linux-aarch64.so.1)
  A3  DT_NEEDED carries no libcrypto/libssl R26: openssl is a system-name
                                           library and is linked statically,
                                           so nothing is added to /lib
  A4  secure_memory_unix.o has an undefined `geteuid` reference
                                           proves the E051 drop_privileges()
                                           guard is really compiled in (the
                                           unpatched translation unit never
                                           calls geteuid).  Requires --object.

Exit code 0 = all executed checks passed, 1 = at least one failure.
"""
import argparse
import json
import struct
import sys

ELFCLASS64 = 2
ELFDATA2LSB = 1
EM_AARCH64 = 183
SHT_SYMTAB = 2
SHT_DYNAMIC = 6
SHN_UNDEF = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_NULL = 0

OHOS_INTERP = "/lib/ld-musl-aarch64.so.1"


class ElfError(Exception):
    pass


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


def _sections(data):
    """Return [(name, sh_type, sh_offset, sh_size, sh_link, sh_entsize)]."""
    if data[:4] != b"\x7fELF":
        raise ElfError("not an ELF file (bad magic %r)" % data[:4])
    if data[4] != ELFCLASS64:
        raise ElfError("not ELF64 (EI_CLASS=%d)" % data[4])
    if data[5] != ELFDATA2LSB:
        raise ElfError("not little-endian (EI_DATA=%d)" % data[5])
    (e_machine,) = struct.unpack_from("<H", data, 18)
    (e_shoff,) = struct.unpack_from("<Q", data, 40)
    (e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHH", data, 58)
    if e_shoff == 0 or e_shnum == 0:
        raise ElfError("no section headers")
    hdrs = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        name, sh_type, _flags, _addr, sh_offset, sh_size, sh_link, _info, \
            _align, sh_entsize = struct.unpack_from("<IIQQQQIIQQ", data, off)
        hdrs.append((name, sh_type, sh_offset, sh_size, sh_link, sh_entsize))
    shstr_off, shstr_size = hdrs[e_shstrndx][2], hdrs[e_shstrndx][3]
    shstr = data[shstr_off:shstr_off + shstr_size]
    out = []
    for name_idx, sh_type, sh_offset, sh_size, sh_link, sh_entsize in hdrs:
        end = shstr.find(b"\x00", name_idx)
        out.append((shstr[name_idx:end].decode("utf-8", "replace"),
                    sh_type, sh_offset, sh_size, sh_link, sh_entsize))
    return e_machine, out


def _section(data, sections, name):
    for sec in sections:
        if sec[0] == name:
            return sec
    return None


def _strtab(data, sections, idx):
    sec = sections[idx]
    return data[sec[2]:sec[2] + sec[3]]


def _cstr(blob, offset):
    end = blob.find(b"\x00", offset)
    return blob[offset:end if end >= 0 else len(blob)].decode("utf-8", "replace")


def check_binary(path):
    """A1-A3 on a linked executable. Returns [(name, ok, detail)]."""
    results = []
    data = _read(path)
    e_machine, sections = _sections(data)

    ok = e_machine == EM_AARCH64
    results.append((
        "A1_elf64_aarch64", ok,
        "ELF64 little-endian, e_machine=%d (%s)" % (
            e_machine, "EM_AARCH64" if ok else "not EM_AARCH64(%d)" % EM_AARCH64)))

    interp = _section(data, sections, ".interp")
    if interp is None:
        results.append(("A2_ohos_musl_interp", False, ".interp section missing"))
    else:
        value = _cstr(data[interp[2]:interp[2] + interp[3]], 0)
        results.append((
            "A2_ohos_musl_interp", value == OHOS_INTERP,
            "PT_INTERP=%s (expected %s)" % (value, OHOS_INTERP)))

    dyn = _section(data, sections, ".dynamic")
    if dyn is None:
        results.append(("A3_static_libcrypto", False, ".dynamic section missing"))
    else:
        strtab = _strtab(data, sections, dyn[4])
        needed, off, blob = [], dyn[2], data
        while off + 16 <= dyn[2] + dyn[3]:
            tag, val = struct.unpack_from("<qQ", blob, off)
            off += 16
            if tag == DT_NULL:
                break
            if tag == DT_NEEDED:
                needed.append(_cstr(strtab, val))
        crypto = [n for n in needed
                  if n.startswith("libcrypto") or n.startswith("libssl")]
        results.append((
            "A3_static_libcrypto", not crypto,
            "DT_NEEDED=%s (crypto shared deps: %s)" % (
                needed or "[]", crypto or "none")))
    return results


def check_object(path):
    """A4 on the relocatable object built from the patched translation unit."""
    data = _read(path)
    _e_machine, sections = _sections(data)
    symtab = None
    for sec in sections:
        if sec[1] == SHT_SYMTAB:
            symtab = sec
            break
    if symtab is None:
        return [("A4_e051_seteuid_guard", False, "no .symtab in %s" % path)]
    strtab = _strtab(data, sections, symtab[4])
    entsize = symtab[5] or 24
    undef = set()
    for i in range(symtab[3] // entsize):
        off = symtab[2] + i * entsize
        st_name, _info, _other, st_shndx = struct.unpack_from("<IBBH", data, off)
        if st_shndx == SHN_UNDEF and st_name:
            undef.add(_cstr(strtab, st_name))
    has_guard = "geteuid" in undef
    return [(
        "A4_e051_seteuid_guard", has_guard,
        "undefined symbols in secure_memory_unix.o: geteuid=%s getuid=%s "
        "seteuid=%s (E051 guard compiled in: %s)" % (
            "geteuid" in undef, "getuid" in undef, "seteuid" in undef,
            has_guard))]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binary", required=True,
                    help="linked secpwgen executable to inspect")
    ap.add_argument("--object", default="",
                    help="optional secure_memory_unix.o for the E051 guard check")
    args = ap.parse_args(argv)

    results = []
    try:
        results.extend(check_binary(args.binary))
        if args.object:
            results.extend(check_object(args.object))
    except (ElfError, OSError, struct.error) as exc:
        print("OHOS_ABI_CHECK_FAILED: %s" % exc)
        return 1

    passed = 0
    for name, ok, detail in results:
        print("[%s] %s: %s" % ("PASS" if ok else "FAIL", name, detail))
        passed += 1 if ok else 0
    summary = {
        "binary": args.binary,
        "discovered": len(results),
        "passed": passed,
        "failed": len(results) - passed,
    }
    print("OHOS_ABI_CHECK=" + json.dumps(summary))
    return 0 if passed == len(results) and results else 1


if __name__ == "__main__":
    sys.exit(main())
