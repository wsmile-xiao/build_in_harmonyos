#!/usr/bin/env python3
"""HarmonyOS artifact/ABI checks for qalc 5.11.0.

Pure-Python ELF inspection, no external tools, so it runs on any build host.
This matters because an aarch64-linux-ohos ELF cannot execute on the macOS
dev box (can_run() is False there); the checks inspect the cross-compiled
artifact instead.  Invoked from the recipe's build() (against the build-tree
binary and library) and from test_package/conanfile.py test() (against the
packaged artifacts).

Checks
  A1  qalc is ELF64 little-endian with e_machine == EM_AARCH64
      (the aarch64-linux-ohos cross triplet is in effect)
  A2  qalc PT_INTERP == /lib/ld-musl-aarch64.so.1
      (OHOS musl loader; a glibc build would use ld-linux-aarch64.so.1)
  A3  qalc DT_NEEDED contains libqalculate.so and no libcurl/libicu
      (the CLI ships with the library it was built from, and the two optional
      deps that are not published for OHOS were really disabled)
  A4  libqalculate.so has no undefined pthread_cancel /
      pthread_setcancelstate / pthread_setcanceltype references
      (proves the HAVE_PTHREAD_* guard patch is compiled in; the unpatched
      build would reference all three, which OHOS musl cannot resolve)

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
DT_NULL = 0

OHOS_INTERP = "/lib/ld-musl-aarch64.so.1"
PTHREAD_CANCEL_FAMILY = ("pthread_cancel", "pthread_setcancelstate",
                         "pthread_setcanceltype")


class ElfError(Exception):
    pass


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


def _sections(data):
    """Return (e_machine, [(name, sh_type, sh_offset, sh_size, sh_link, sh_entsize)])."""
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


def _needed(data, sections):
    dyn = _section(data, sections, ".dynamic")
    if dyn is None:
        raise ElfError(".dynamic section missing")
    strtab = _strtab(data, sections, dyn[4])
    needed, off = [], dyn[2]
    while off + 16 <= dyn[2] + dyn[3]:
        tag, val = struct.unpack_from("<qQ", data, off)
        off += 16
        if tag == DT_NULL:
            break
        if tag == DT_NEEDED:
            needed.append(_cstr(strtab, val))
    return needed


def _undefined(data, sections):
    symtab = None
    for sec in sections:
        if sec[1] == SHT_SYMTAB:
            symtab = sec
            break
    if symtab is None:
        raise ElfError("no .symtab section")
    strtab = _strtab(data, sections, symtab[4])
    entsize = symtab[5] or 24
    undef = set()
    for i in range(symtab[3] // entsize):
        off = symtab[2] + i * entsize
        st_name, _info, _other, st_shndx = struct.unpack_from("<IBBH", data, off)
        if st_shndx == SHN_UNDEF and st_name:
            undef.add(_cstr(strtab, st_name))
    return undef


def check_binary(path):
    """A1-A3 on the qalc executable. Returns [(name, ok, detail)]."""
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

    needed = _needed(data, sections)
    has_qalculate = any(n.startswith("libqalculate.so") for n in needed)
    optional = [n for n in needed
                if n.startswith("libcurl") or n.startswith("libicu")]
    ok3 = has_qalculate and not optional
    results.append((
        "A3_dtneeded_self_contained", ok3,
        "DT_NEEDED=%s (libqalculate=%s, libcurl/libicu=%s)" % (
            needed or "[]", has_qalculate, optional or "none")))

    return results


def check_lib(path):
    """A4 on libqalculate.so: pthread_cancel family must not be referenced."""
    data = _read(path)
    _e_machine, sections = _sections(data)
    undef = _undefined(data, sections)
    present = [s for s in PTHREAD_CANCEL_FAMILY if s in undef]
    return [(
        "A4_pthread_cancel_guarded", not present,
        "undefined pthread_cancel-family symbols in libqalculate.so: %s "
        "(guard compiled in: %s)" % (present or "none", not present))]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binary", required=True,
                    help="packaged qalc executable to inspect")
    ap.add_argument("--lib", default="",
                    help="libqalculate.so for the pthread guard check")
    args = ap.parse_args(argv)

    results = []
    try:
        results.extend(check_binary(args.binary))
        if args.lib:
            results.extend(check_lib(args.lib))
    except (ElfError, OSError, struct.error) as exc:
        print("OHOS_ABI_CHECK_FAILED: %s" % exc)
        return 1

    passed = 0
    for name, ok, detail in results:
        print("[%s] %s: %s" % ("PASS" if ok else "FAIL", name, detail))
        passed += 1 if ok else 0
    summary = {
        "binary": args.binary,
        "lib": args.lib,
        "discovered": len(results),
        "passed": passed,
        "failed": len(results) - passed,
    }
    print("OHOS_ABI_CHECK=" + json.dumps(summary))
    return 0 if passed == len(results) and results else 1


if __name__ == "__main__":
    sys.exit(main())
