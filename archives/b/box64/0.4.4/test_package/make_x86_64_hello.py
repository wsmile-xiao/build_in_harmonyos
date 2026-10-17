#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_x86_64_hello.py -- generate a minimal, self-contained x86_64 ELF
executable using only the Python standard library.

Why: box64 test assets must be text-only in the recipe repo, so we cannot
ship a precompiled x86_64 binary.  This script recreates a tiny static
ET_EXEC ELF at build/test time (pure bytes, no cross toolchain needed).

What it makes:
  * x86-64 (EM_X86_64, little-endian, ELFCLASS64) ET_EXEC, static
  * one PT_LOAD (R+X) segment based at 0x400000
  * raw-syscall code: write(1, msg, len); exit(code)
  * default: prints one line "hello from x86_64" and exits 0

Usage:
  python3 make_x86_64_hello.py [-o hello_x86_64] [--msg TEXT] [--exit-code N] [--verify]

Expected output when executed (e.g. via box64):
  hello from x86_64
  exit status 0
"""

import argparse
import os
import struct
import sys

BASE = 0x400000          # classic static PIE-free load address
EHDR_SIZE = 64           # sizeof(Elf64_Ehdr)
PHDR_SIZE = 56           # sizeof(Elf64_Phdr)
NPHDR = 1
CODE_OFF = EHDR_SIZE + PHDR_SIZE  # file offset of code = 120 (0x78)
DEFAULT_MSG = "hello from x86_64\n"

# --- x86-64 instruction encoders -------------------------------------------

def mov_r32_imm32(reg, val):
    """mov r32, imm32  (B8+rd id) -- zero-extends to 64-bit."""
    return bytes([0xB8 + reg]) + struct.pack("<I", val & 0xFFFFFFFF)

def mov_r64_imm64(reg, val):
    """mov r64, imm64  (REX.W + B8+rd io)."""
    assert 0 <= reg < 8
    return bytes([0x48, 0xB8 + reg]) + struct.pack("<Q", val & 0xFFFFFFFFFFFFFFFF)

def build_code(msg_off, msg_len, exit_code):
    code = b""
    code += mov_r32_imm32(0, 1)                 # eax = __NR_write
    code += mov_r32_imm32(7, 1)                 # edi = STDOUT_FILENO
    code += mov_r64_imm64(6, BASE + msg_off)    # rsi = &msg
    code += mov_r32_imm32(2, msg_len)           # edx = len
    code += b"\x0f\x05"                         # syscall
    code += mov_r32_imm32(0, 60)                # eax = __NR_exit
    code += mov_r32_imm32(7, exit_code)         # edi = exit code
    code += b"\x0f\x05"                         # syscall
    return code

def build_elf(msg, exit_code):
    msg = msg.encode("utf-8") if isinstance(msg, str) else bytes(msg)
    code = build_code(CODE_OFF + 36, len(msg), exit_code)
    # msg_off was provisional (code length is fixed); recompute exactly:
    code = build_code(CODE_OFF + len(code), len(msg), exit_code)
    msg_off = CODE_OFF + len(code)
    total = msg_off + len(msg)

    e_ident = b"\x7fELF" + bytes([2, 1, 1, 0]) + b"\x00" * 8  # ELF64, LE, v1, SysV
    ehdr = e_ident + struct.pack(
        "<HHIQQQIHHHHHH",
        2,          # e_type    = ET_EXEC
        0x3E,       # e_machine = EM_X86_64
        1,          # e_version
        BASE + CODE_OFF,  # e_entry
        EHDR_SIZE,  # e_phoff
        0,          # e_shoff (no section headers)
        0,          # e_flags
        EHDR_SIZE,  # e_ehsize
        PHDR_SIZE,  # e_phentsize
        NPHDR,      # e_phnum
        0, 0, 0,    # e_shentsize, e_shnum, e_shstrndx
    )
    assert len(ehdr) == EHDR_SIZE, len(ehdr)

    phdr = struct.pack(
        "<IIQQQQQQ",
        1,          # p_type   = PT_LOAD
        5,          # p_flags  = PF_R | PF_X
        0,          # p_offset
        BASE,       # p_vaddr
        BASE,       # p_paddr
        total,      # p_filesz
        total,      # p_memsz
        0x1000,     # p_align
    )
    assert len(phdr) == PHDR_SIZE, len(phdr)

    return ehdr + phdr + code + msg, msg_off

def verify(path):
    """Parse back the ELF we generated (independent structural check)."""
    data = open(path, "rb").read()
    assert data[:4] == b"\x7fELF", "not an ELF"
    assert data[4] == 2, "not ELFCLASS64"
    assert data[5] == 1, "not little-endian"
    e_type, e_machine = struct.unpack_from("<HH", data, 16)
    e_entry = struct.unpack_from("<Q", data, 24)[0]
    e_phoff, e_shoff = struct.unpack_from("<QQ", data, 32)
    e_phnum = struct.unpack_from("<H", data, 56)[0]
    p_type, p_flags = struct.unpack_from("<II", data, e_phoff)
    p_off, p_vaddr, p_paddr = struct.unpack_from("<QQQ", data, e_phoff + 8)
    p_filesz, p_memsz = struct.unpack_from("<QQ", data, e_phoff + 32)
    ok = (
        e_type == 2 and e_machine == 0x3E and e_phnum == 1
        and e_entry == BASE + CODE_OFF and e_phoff == EHDR_SIZE
        and e_shoff == 0 and p_type == 1 and p_flags == 5
        and p_off == 0 and p_vaddr == BASE == p_paddr
        and p_filesz == p_memsz == len(data)
    )
    print("verify: %s" % ("OK" if ok else "FAILED"))
    print("  size      : %d bytes" % len(data))
    print("  type/mach : ET_EXEC / EM_X86_64 (0x3E)" if e_type == 2 and e_machine == 0x3E
          else "  type/mach : UNEXPECTED")
    print("  entry     : 0x%x" % e_entry)
    print("  PT_LOAD   : off=0x%x vaddr=0x%x flags=%d filesz=0x%x" %
          (p_off, p_vaddr, p_flags, p_filesz))
    return ok

def main():
    ap = argparse.ArgumentParser(description="generate a minimal x86_64 ELF")
    ap.add_argument("-o", "--out", default="hello_x86_64",
                    help="output path (default: hello_x86_64)")
    ap.add_argument("--msg", default=DEFAULT_MSG,
                    help="bytes to write to stdout (default: %r)" % DEFAULT_MSG)
    ap.add_argument("--exit-code", type=int, default=0, help="exit status (default 0)")
    ap.add_argument("--verify", action="store_true",
                    help="parse the generated file back and print a summary")
    args = ap.parse_args()

    blob, msg_off = build_elf(args.msg, args.exit_code & 0xFF)
    with open(args.out, "wb") as f:
        f.write(blob)
    os.chmod(args.out, 0o755)

    print("wrote %s (%d bytes, message at 0x%x)" % (args.out, len(blob), BASE + msg_off))
    expected = args.msg if isinstance(args.msg, str) else args.msg.decode("utf-8", "replace")
    print("expected stdout: %r" % expected)
    print("expected exit  : %d" % args.exit_code)
    if args.verify:
        sys.exit(0 if verify(args.out) else 1)

if __name__ == "__main__":
    main()
