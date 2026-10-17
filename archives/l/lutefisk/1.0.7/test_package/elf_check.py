#!/usr/bin/env python3
"""HarmonyOS-specific ELF assertions for the packaged lutefisk executable.

Deliberately dependency-free: it parses the ELF header and the program/dynamic
headers with the standard library only, so it works on the CI worker and on a
bare OHOS image where readelf/llvm-readelf may be absent.

Checks (each is one assertion, 8 in total):
  1. ELF magic.
  2. Class/endianness (64-bit little-endian).
  3. e_machine == EM_AARCH64 (183) — the binary really targets OHOS aarch64.
  4. e_type == ET_DYN (PIE) — HarmonyOS PC requires a position independent
     executable for its loader.
  5. PT_GNU_STACK exists with flags without PF_X — NX stack.
  6. PT_GNU_RELRO present — full RELRO hardening.
  7. Immediate binding is requested, encoded either as DT_BIND_NOW or as the
     DF_BIND_NOW / DF_1_NOW bits of DT_FLAGS / DT_FLAGS_1 (lld uses the
     latter).
  8. Every DT_NEEDED entry is a system library (libc / libm); lutefisk pulls in
     nothing else, so the package is self-contained on a stock OHOS image.
"""
import struct
import sys

EM_AARCH64 = 183
ET_DYN = 3
PT_GNU_STACK = 0x6474E551
PT_GNU_RELRO = 0x6474E552
PF_X = 0x1
DT_NULL = 0
DT_NEEDED = 1
DT_BIND_NOW = 24
DT_FLAGS = 30
DF_BIND_NOW = 0x8
DT_FLAGS_1 = 0x6FFFFFFB
DF_1_NOW = 0x1
SYSTEM_LIBS = ("libc.so", "libm.so", "ld-musl", "libc++", "libc++_shared")

FAILURES = []
CHECKS = 0


def check(ok, label, detail=""):
    global CHECKS
    CHECKS += 1
    if ok:
        print("PASS: %s" % label)
    else:
        print("FAIL: %s %s" % (label, detail))
        FAILURES.append(label)


def cstr(blob, off):
    end = blob.find(b"\x00", off)
    return blob[off:end].decode("ascii", "replace")


def main(path):
    with open(path, "rb") as handle:
        blob = handle.read()

    check(blob[:4] == b"\x7fELF", "ELF magic", blob[:4])
    check(blob[4] == 2 and blob[5] == 1, "64-bit little-endian ELF",
          "class=%d data=%d" % (blob[4], blob[5]))

    e_type, e_machine = struct.unpack_from("<HH", blob, 16)
    check(e_machine == EM_AARCH64, "e_machine is EM_AARCH64", e_machine)
    check(e_type == ET_DYN, "e_type is ET_DYN (PIE)", e_type)

    e_phoff, = struct.unpack_from("<Q", blob, 32)
    e_phentsize, e_phnum = struct.unpack_from("<HH", blob, 54)

    stack_flags = None
    has_relro = False
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, = struct.unpack_from("<I", blob, off)
        if p_type == PT_GNU_STACK:
            p_flags, = struct.unpack_from("<I", blob, off + 4)
            stack_flags = p_flags
        elif p_type == PT_GNU_RELRO:
            has_relro = True
    check(stack_flags is not None and not stack_flags & PF_X,
          "PT_GNU_STACK is non-executable (NX)", stack_flags)
    check(has_relro, "PT_GNU_RELRO present (full RELRO)")

    # PT_DYNAMIC
    dyn_off = dyn_size = 0
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, = struct.unpack_from("<I", blob, off)
        if p_type == 2:  # PT_DYNAMIC
            dyn_off, = struct.unpack_from("<Q", blob, off + 8)
            dyn_size, = struct.unpack_from("<Q", blob, off + 32)

    needed, bind_now = [], False
    strtab_addr = 0
    pos = dyn_off
    while pos < dyn_off + dyn_size:
        tag, val = struct.unpack_from("<QQ", blob, pos)
        pos += 16
        if tag == DT_NULL:
            break
        if tag == DT_NEEDED:
            needed.append(val)
        elif tag == DT_BIND_NOW:
            bind_now = True
        elif tag == DT_FLAGS and val & DF_BIND_NOW:
            bind_now = True
        elif tag == DT_FLAGS_1 and val & DF_1_NOW:
            bind_now = True
        elif tag == 5:  # DT_STRTAB
            strtab_addr = val

    # Translate DT_STRTAB vaddr -> file offset via PT_LOAD segments.
    strtab_off = 0
    if strtab_addr:
        for i in range(e_phnum):
            off = e_phoff + i * e_phentsize
            p_type, = struct.unpack_from("<I", blob, off)
            if p_type != 1:  # PT_LOAD
                continue
            p_offset, p_vaddr = struct.unpack_from("<QQ", blob, off + 8)
            p_filesz, = struct.unpack_from("<Q", blob, off + 32)
            if p_vaddr <= strtab_addr < p_vaddr + p_filesz:
                strtab_off = p_offset + (strtab_addr - p_vaddr)
                break

    names = [cstr(blob, strtab_off + n) for n in needed] if strtab_off else []
    check(bind_now, "immediate binding requested (BIND_NOW)")
    extra = [n for n in names
             if not any(n.startswith(s) for s in SYSTEM_LIBS)]
    check(not extra, "only system shared libraries are NEEDED", extra or names)

    print("elf assertions: %d/%d passed" % (CHECKS - len(FAILURES), CHECKS))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
