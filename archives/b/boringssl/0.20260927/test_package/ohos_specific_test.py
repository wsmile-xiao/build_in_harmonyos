#!/usr/bin/env python3
"""R53 鸿蒙特有测试 — boringssl/0.20260927（鸿蒙适配路径实际运行 + 断言）。

在鸿蒙 PC 上实际运行，断言本包的鸿蒙适配决策真实生效（无 readelf 依赖，
纯 Python 结构解析，CI worker 缺 readelf 亦可运行）：

  1. 系统同名库静态交付（R26）：libssl.a / libcrypto.a 存在，且包内无 .so
  2. bssl CLI 为鸿蒙目标产物：ELF64 / AArch64 / PIE / musl 解释器
  3. 无 RPATH/RUNPATH；动态 NEEDED 不含 libssl/libcrypto（静态链接生效）
  4. 安全加固：GNU_RELRO + BIND_NOW（full RELRO）；GNU_STACK 不可执行（NX）
  5. 实际运行 bssl sha256sum 并与 Python hashlib 已知向量比对；
     实跑 bssl rand 16（熵源路径）
  6. 静态库包含被测 API 符号（BN_mod_exp / SSL_CTX_new）
  7. 头文件交付完整（openssl/ssl.h、crypto.h、evp.h、bn.h）

退出码：0 = 全部通过；1 = 存在失败。
用法：python3 ohos_specific_test.py --pkg <package_folder>
"""
from __future__ import annotations

import argparse
import hashlib
import os
import struct
import subprocess
import sys

# ELF 常量
ELFCLASS64 = 2
ET_DYN = 3
EM_AARCH64 = 0xB7
PT_LOAD, PT_DYNAMIC, PT_INTERP = 1, 2, 3
PT_GNU_STACK = 0x6474E551
PT_GNU_RELRO = 0x6474E552
DT_NULL, DT_NEEDED, DT_RPATH, DT_RUNPATH, DT_FLAGS, DT_FLAGS_1 = 0, 1, 15, 29, 30, 0x6FFFFFFB
DF_BIND_NOW = 0x8
DF_1_NOW = 0x1
PF_X = 0x1

CHECKS = 0
FAILURES = 0


def check(ok: bool, what: str) -> None:
    global CHECKS, FAILURES
    CHECKS += 1
    if ok:
        print(f"ok {CHECKS} - {what}")
    else:
        print(f"FAIL {CHECKS} - {what}")
        FAILURES += 1


def parse_elf(path: str) -> dict:
    """纯 Python 解析 ELF64（仅取本测试需要的字段）。"""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF":
        raise ValueError(f"{path}: not an ELF file")
    ei_class = data[4]
    e_type = struct.unpack_from("<H", data, 16)[0]
    e_machine = struct.unpack_from("<H", data, 18)[0]
    e_phoff = struct.unpack_from("<Q", data, 32)[0]
    e_phentsize = struct.unpack_from("<H", data, 54)[0]
    e_phnum = struct.unpack_from("<H", data, 56)[0]

    phdrs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, p_flags = struct.unpack_from("<II", data, off)
        p_offset, p_vaddr, p_paddr, p_filesz, p_memsz = struct.unpack_from(
            "<QQQQQ", data, off + 8)
        phdrs.append({"type": p_type, "flags": p_flags, "offset": p_offset,
                      "vaddr": p_vaddr, "filesz": p_filesz})

    info = {
        "class": ei_class,
        "type": e_type,
        "machine": e_machine,
        "phdrs": phdrs,
        "interp": None,
        "needed": [],
        "rpath": [],
        "bind_now": False,
        "relro": False,
        "stack_exec": False,
        "data": data,
    }
    for ph in phdrs:
        if ph["type"] == PT_INTERP:
            raw = data[ph["offset"]:ph["offset"] + ph["filesz"]]
            info["interp"] = raw.split(b"\x00", 1)[0].decode("utf-8", "replace")
        if ph["type"] == PT_GNU_RELRO:
            info["relro"] = True
        if ph["type"] == PT_GNU_STACK:
            info["stack_exec"] = bool(ph["flags"] & PF_X)

    # 动态段
    def read_cstr(off: int) -> str:
        end = data.index(b"\x00", off)
        return data[off:end].decode("utf-8", "replace")

    dyn = next((ph for ph in phdrs if ph["type"] == PT_DYNAMIC), None)
    if dyn is not None:
        # PT_DYNAMIC 的 offset 即文件偏移；链接地址与文件偏移在本测试中无需换算
        # strtab 需第二次遍历取 DT_STRTAB
        entries = []
        n = dyn["filesz"] // 16
        for i in range(n):
            off = dyn["offset"] + i * 16
            tag, val = struct.unpack_from("<qQ", data, off)
            entries.append((tag, val))
            if tag == DT_NULL:
                break
        strtab_vaddr = next((v for t, v in entries if t == 5), 0)
        # 将 vaddr 映射到文件偏移（PT_LOAD: file_off = p_offset + (vaddr - p_vaddr)）
        strtab_off = None
        for ph in phdrs:
            if ph["type"] == PT_LOAD and \
                    ph["vaddr"] <= strtab_vaddr < ph["vaddr"] + ph["filesz"]:
                strtab_off = ph["offset"] + (strtab_vaddr - ph["vaddr"])
                break
        if strtab_off is not None:
            for t, v in entries:
                if t == DT_NEEDED:
                    info["needed"].append(read_cstr(strtab_off + v))
                elif t in (DT_RPATH, DT_RUNPATH):
                    info["rpath"].append(read_cstr(strtab_off + v))
                elif t == DT_FLAGS and (v & DF_BIND_NOW):
                    info["bind_now"] = True
                elif t == DT_FLAGS_1 and (v & DF_1_NOW):
                    info["bind_now"] = True
    return info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True, help="boringssl 包目录")
    args = ap.parse_args()
    pkg = os.path.abspath(args.pkg)
    print(f"== R53 OHOS-specific test: boringssl (pkg={pkg}) ==")

    # 1. 系统同名库静态交付（R26）
    libdir = os.path.join(pkg, "lib")
    libssl_a = os.path.join(libdir, "libssl.a")
    libcrypto_a = os.path.join(libdir, "libcrypto.a")
    check(os.path.isfile(libssl_a), "R26: libssl.a present (static)")
    check(os.path.isfile(libcrypto_a), "R26: libcrypto.a present (static)")
    shared = []
    for root, _dirs, files in os.walk(pkg):
        for name in files:
            if name.endswith(".so") or ".so." in name:
                shared.append(os.path.join(root, name))
    check(not shared, "R26: no .so in package (system-name libs never shipped shared)")
    if shared:
        print("    unexpected shared libs:", shared)

    # 2. bssl CLI ELF 元数据
    bssl = os.path.join(pkg, "bin", "bssl")
    check(os.path.isfile(bssl), "bssl CLI installed to bin/")
    if not os.path.isfile(bssl):
        print(f"R53_RESULT=FAIL ({CHECKS - FAILURES}/{CHECKS})")
        return 1
    elf = parse_elf(bssl)
    check(elf["class"] == ELFCLASS64, "bssl is ELF64")
    check(elf["machine"] == EM_AARCH64, "bssl e_machine=AArch64")
    check(elf["type"] == ET_DYN, "bssl is PIE (ET_DYN)")
    interp = elf["interp"] or ""
    check("ld-musl" in interp or "ohos" in interp,
          f"bssl interpreter is OHOS musl ({interp})")

    # 3. 静态链接 + 无 RPATH
    check(not elf["rpath"], "bssl has no RPATH/RUNPATH")
    check(not any("libssl" in n or "libcrypto" in n for n in elf["needed"]),
          f"bssl NEEDED excludes libssl/libcrypto (static: {elf['needed']})")

    # 4. 安全加固
    check(elf["relro"], "bssl has GNU_RELRO segment")
    check(elf["bind_now"], "bssl has BIND_NOW (full RELRO)")
    check(not elf["stack_exec"], "bssl GNU_STACK is non-executable (NX)")

    # 5. 实际运行（鸿蒙真机路径）
    payload = b"boringssl-ohos\n"
    proc = subprocess.run([bssl, "sha256sum"], input=payload,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=60)
    out = proc.stdout.decode("utf-8", "replace").strip()
    expected = hashlib.sha256(payload).hexdigest()
    check(proc.returncode == 0 and out.split() and out.split()[0] == expected,
          f"bssl sha256sum runs on OHOS and matches known vector ({expected[:16]}…)")
    help_proc = subprocess.run([bssl, "rand", "16"], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=60)
    check(help_proc.returncode == 0 and len(help_proc.stdout) == 16,
          "bssl rand 16 runs on OHOS (entropy path, 16 bytes)")

    # 6. 静态库符号
    with open(libcrypto_a, "rb") as fh:
        crypto_bytes = fh.read()
    with open(libssl_a, "rb") as fh:
        ssl_bytes = fh.read()
    check(crypto_bytes[:8] == b"!<arch>\n", "libcrypto.a is an ar archive")
    check(ssl_bytes[:8] == b"!<arch>\n", "libssl.a is an ar archive")
    check(b"BN_mod_exp" in crypto_bytes, "libcrypto.a exports BN_mod_exp symbol")
    check(b"SSL_CTX_new" in ssl_bytes, "libssl.a exports SSL_CTX_new symbol")

    # 7. 头文件交付
    inc = os.path.join(pkg, "include", "openssl")
    for header in ("ssl.h", "crypto.h", "evp.h", "bn.h"):
        check(os.path.isfile(os.path.join(inc, header)),
              f"header include/openssl/{header} delivered")

    total = CHECKS
    passed = CHECKS - FAILURES
    if FAILURES:
        print(f"R53_RESULT=FAIL ({passed}/{total})")
        return 1
    print(f"ALL OHOS SPECIFIC TESTS PASSED ({passed}/{total})")
    print("R53_RESULT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
