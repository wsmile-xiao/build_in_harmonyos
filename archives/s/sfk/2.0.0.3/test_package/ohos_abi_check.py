#!/usr/bin/env python3
"""HarmonyOS artifact/ABI checks for sfk 2.0.0.3 (pure Python, no external tools).

HarmonyOS-specific test cases that inspect the packaged artifact instead of
executing it. They are invoked from test_package/conanfile.py on the packaged
binary (can_run() True on the HarmonyOS worker).

Checks
  A1  ELF64 + e_machine == EM_AARCH64      HarmonyOS PC arm64 target
  A2  .interp == /lib/ld-musl-aarch64.so.1 OHOS musl loader (glibc would be
                                           /lib/ld-linux-aarch64.so.1)

Exit code 0 = all executed checks passed, 1 = at least one failure.
"""
import argparse
import json
import struct
import sys

ELFCLASS64 = 2
ELFDATA2LSB = 1
EM_AARCH64 = 183

OHOS_INTERP = "/lib/ld-musl-aarch64.so.1"


class ElfError(Exception):
    pass


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


def _sections(data):
    """Return (e_machine, [(name, sh_offset, sh_size)])."""
    if data[:4] != b"\x7fELF":
        raise ElfError("not an ELF file (bad magic)")
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
        _name, _type, _flags, _addr, sh_offset, sh_size, _link, _info, \
            _align, _entsize = struct.unpack_from("<IIQQQQIIQQ", data, off)
        hdrs.append((sh_offset, sh_size))
    shstr_off, shstr_size = hdrs[e_shstrndx][0], hdrs[e_shstrndx][1]
    shstr = data[shstr_off:shstr_off + shstr_size]
    names = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        (name_idx,) = struct.unpack_from("<I", data, off)
        end = shstr.find(b"\x00", name_idx)
        names.append(shstr[name_idx:end].decode("utf-8", "replace"))
    out = [
        (names[i], hdrs[i][0], hdrs[i][1])
        for i in range(e_shnum)
    ]
    return e_machine, out


def _cstr(blob, offset):
    end = blob.find(b"\x00", offset)
    return blob[offset:end if end >= 0 else len(blob)].decode("utf-8", "replace")


def check_binary(path):
    """A1-A2 on the packaged executable. Returns [(name, ok, detail)]."""
    data = _read(path)
    e_machine, sections = _sections(data)

    ok_a1 = e_machine == EM_AARCH64
    a1_detail = "ELF64 little-endian, e_machine=%d (%s)" % (
        e_machine, "EM_AARCH64" if ok_a1 else "not EM_AARCH64(%d)" % EM_AARCH64)

    interp_sec = next((s for s in sections if s[0] == ".interp"), None)
    if interp_sec is None:
        a2_detail = ".interp section missing"
        ok_a2 = False
    else:
        value = _cstr(data[interp_sec[1]:interp_sec[1] + interp_sec[2]], 0)
        ok_a2 = value == OHOS_INTERP
        a2_detail = "PT_INTERP=%s (expected %s)" % (value, OHOS_INTERP)

    return [
        ("A1_elf64_aarch64", ok_a1, a1_detail),
        ("A2_ohos_musl_interp", ok_a2, a2_detail),
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binary", required=True,
                    help="packaged sfk executable to inspect")
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
    return 0 if results and passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
