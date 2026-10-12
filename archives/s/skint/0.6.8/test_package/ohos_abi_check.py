#!/usr/bin/env python3
"""HarmonyOS artifact/ABI checks for skint 0.6.8 (pure Python, no external tools).

These are HarmonyOS-specific test cases that can be evaluated on *any* build
host, because they inspect the cross-compiled artifact instead of executing it
(an aarch64-linux-ohos ELF cannot run on the macOS dev box that only simulates
the OHOS worker, where can_run() is False).  They are invoked from
test_package/conanfile.py test() on the *packaged* binary, so the CI L1e
destructive reverse check (move bin/ away -> re-run) still fails correctly.

Checks
  A1  ELF64 little-endian + e_machine == EM_AARCH64
      HarmonyOS PC is aarch64; a host x86 build of skint would fail here.
  A2  .interp == /lib/ld-musl-aarch64.so.1
      OHOS ships musl.  A glibc-targeted aarch64 toolchain would emit
      /lib/ld-linux-aarch64.so.1, so this separates "really built for OHOS"
      from "built for some other aarch64 Linux".
  A3  DT_NEEDED == ["libc.so"] exactly
      skint links -lm, and on the OHOS musl sysroot libm is folded into
      libc.so, so the only recorded dependency is libc.so.  Any aarch64 glibc
      build would additionally record libm.so.6 -- this assertion therefore
      pins the musl libc layout that HarmonyOS actually has.
  A4  no DT_RPATH / DT_RUNPATH
      OHOS packages are staged into a versioned prefix and moved out of the
      conan cache; a build-path RPATH would make the loader look for
      directories that only exist on the build machine.

Exit code 0 = every requested check passed, 1 = at least one failure.
"""
import argparse
import json
import struct
import sys

ELFCLASS64 = 2
ELFDATA2LSB = 1
EM_AARCH64 = 183
SHT_DYNAMIC = 6
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_RPATH = 15
DT_RUNPATH = 29

OHOS_INTERP = "/lib/ld-musl-aarch64.so.1"
EXPECTED_NEEDED = ["libc.so"]


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


def _section(sections, name):
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
    """A1-A4 on a linked executable. Returns [(name, ok, detail)]."""
    data = _read(path)
    e_machine, sections = _sections(data)
    results = []

    ok = e_machine == EM_AARCH64
    results.append((
        "A1_elf64_aarch64", ok,
        "ELF64 little-endian, e_machine=%d (%s)" % (
            e_machine, "EM_AARCH64" if ok else "not EM_AARCH64(%d)" % EM_AARCH64)))

    interp = _section(sections, ".interp")
    if interp is None:
        results.append(("A2_ohos_musl_interp", False, ".interp section missing"))
    else:
        value = _cstr(data[interp[2]:interp[2] + interp[3]], 0)
        results.append((
            "A2_ohos_musl_interp", value == OHOS_INTERP,
            "PT_INTERP=%s (expected %s)" % (value, OHOS_INTERP)))

    dyn = _section(sections, ".dynamic")
    if dyn is None:
        results.append(("A3_musl_libm_folded", False, ".dynamic section missing"))
        results.append(("A4_no_rpath", False, ".dynamic section missing"))
        return results
    strtab = _strtab(data, sections, dyn[4])
    needed, paths, off = [], [], dyn[2]
    while off + 16 <= dyn[2] + dyn[3]:
        tag, val = struct.unpack_from("<qQ", data, off)
        off += 16
        if tag == DT_NULL:
            break
        if tag == DT_NEEDED:
            needed.append(_cstr(strtab, val))
        elif tag in (DT_RPATH, DT_RUNPATH):
            paths.append(_cstr(strtab, val))
    results.append((
        "A3_musl_libm_folded", sorted(needed) == EXPECTED_NEEDED,
        "DT_NEEDED=%s (expected exactly %s: musl folds libm into libc.so)"
        % (needed or "[]", EXPECTED_NEEDED)))
    results.append((
        "A4_no_rpath", not paths,
        "DT_RPATH/DT_RUNPATH=%s (must be empty so the OHOS loader searches "
        "system paths)" % (paths or "[]")))
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binary", required=True,
                    help="packaged skint executable to inspect")
    args = ap.parse_args(argv)

    try:
        results = check_binary(args.binary)
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
