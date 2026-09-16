#!/usr/bin/env python3
"""消费测试：cdtool 2.1.8-release 安装布局 + OHOS 产物属性 + 真实运行。

用法: python3 test_cdtool.py <package_folder>

被测事实（全部来自真实安装目录，不依赖源码树）：
  1. lib/cdtool/cdtool 存在且是可执行的常规文件（非符号链接、非空）
  2. 该产物是 64 位小端 AArch64 ELF、类型 DYN（PIE）        ← 鸿蒙特有
  3. 该产物内嵌 OHOS musl 加载器路径 /lib/ld-musl-aarch64.so.1 ← 鸿蒙特有
  4. 该产物不依赖 glibc（无 libc.so.6 字符串）                ← 鸿蒙特有
  5. bin/ 下 10 个别名是符号链接、指向 ../lib/cdtool/cdtool、且可解析
  6. bin/ 下 5 个独立产物存在且可执行
  7. share/man/man1 下 16 份手册页，别名手册指向 cdtool.1
  8. 真实运行：cdplay/cdtool -V、cdctrl -h、cdown -V、cdtool2cddb -h 均 rc=0
  9. 如实记录：bin/ 下没有名为 cdtool 的入口；上游无自动化测试套件

终态由各检查结果推导：任一 FAIL 即 exit 1，全部 PASS 才打印 ALL PASS。
"""
import os
import struct
import subprocess
import sys

PASS = "PASS:"
FAIL = "FAIL:"
NOTE = "NOTE:"

# 上游 Makefile.in 的 LINKS（单程序多名字的别名集合）
ALIASES = ["cdplay", "cdpause", "cdstop", "cdclose", "cdeject",
           "cdir", "cdinfo", "cdreset", "cdvolume", "cdshuffle"]
# 上游 Makefile.in install-files 安装的独立产物
PROGRAMS = ["cdctrl", "cdown", "cdadd", "cdloop", "cdtool2cddb"]
LINK_TARGET = "../lib/cdtool/cdtool"
MUSL_LOADER = b"/lib/ld-musl-aarch64.so.1"

failures = []


def check(cond, ok_msg, fail_msg):
    if cond:
        print(f"{PASS} {ok_msg}")
    else:
        print(f"{FAIL} {fail_msg}")
        failures.append(fail_msg)
    return bool(cond)


def elf_header(path):
    with open(path, "rb") as fh:
        head = fh.read(64)
    if head[:4] != b"\x7fELF":
        return None
    ei_class, ei_data = head[4], head[5]
    e_type = struct.unpack_from("<H", head, 16)[0]
    e_machine = struct.unpack_from("<H", head, 18)[0]
    return ei_class, ei_data, e_type, e_machine


def run(argv, timeout=30):
    with open(os.devnull, "r") as devnull:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout, stdin=devnull)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main():
    pkg = sys.argv[1]
    bindir = os.path.join(pkg, "bin")
    man1 = os.path.join(pkg, "share", "man", "man1")
    main_exe = os.path.join(pkg, "lib", "cdtool", "cdtool")

    # ── 1. 主程序存在、是常规可执行文件 ────────────────────────────────
    if not check(os.path.isfile(main_exe) and not os.path.islink(main_exe),
                 "lib/cdtool/cdtool 存在且为常规文件（非符号链接）",
                 "lib/cdtool/cdtool 缺失或为符号链接"):
        print(f"{FAIL} 主程序缺失，后续检查无法进行")
        sys.exit(1)
    check(os.access(main_exe, os.X_OK) and os.path.getsize(main_exe) > 0,
          f"lib/cdtool/cdtool 可执行且非空（{os.path.getsize(main_exe)} B）",
          "lib/cdtool/cdtool 不可执行或为空")

    # ── 2. ELF 身份：aarch64 + PIE ───────────────────────────────────
    hdr = elf_header(main_exe)
    if hdr:
        ei_class, ei_data, e_type, e_machine = hdr
        check(ei_class == 2 and ei_data == 1,
              "ELF 为 64 位小端（ELFCLASS64 + ELFDATA2LSB）",
              f"ELF 类别/字节序异常（class={ei_class} data={ei_data}）")
        check(e_machine == 0xB7, "ELF 目标架构为 AArch64（e_machine=0xB7）",
              f"ELF 架构非 AArch64（e_machine=0x{e_machine:x}）")
        check(e_type == 3, "ELF 类型为 DYN（位置无关可执行 PIE，e_type=3）",
              f"ELF 类型非 PIE（e_type={e_type}）")
    else:
        check(False, "", "非 ELF 文件")

    raw = open(main_exe, "rb").read()
    # ── 3. 内嵌 OHOS musl 动态加载器路径 ─────────────────────────────
    check(MUSL_LOADER in raw,
          f"产物内嵌 OHOS musl 加载器路径 {MUSL_LOADER.decode()}",
          "产物未内嵌 OHOS musl 加载器路径（可能是 glibc 或静态产物）")
    # ── 4. 不依赖 glibc ─────────────────────────────────────────────
    check(b"libc.so.6" not in raw,
          "产物不引用 glibc 的 libc.so.6",
          "产物引用了 glibc 的 libc.so.6（链接到了错误的目标平台）")

    # ── 5. 10 个别名符号链接 ─────────────────────────────────────────
    alias_ok = 0
    for name in ALIASES:
        path = os.path.join(bindir, name)
        if os.path.islink(path) and os.readlink(path) == LINK_TARGET \
                and os.path.exists(path):
            alias_ok += 1
        else:
            print(f"{FAIL} bin/{name} 不是指向 {LINK_TARGET} 的有效符号链接")
            failures.append(f"bin/{name} 符号链接异常")
    check(alias_ok == len(ALIASES),
          f"bin/ 下 {len(ALIASES)} 个别名符号链接均指向 {LINK_TARGET} 且可解析",
          f"仅 {alias_ok}/{len(ALIASES)} 个别名符号链接正确")

    # ── 6. 5 个独立产物 ─────────────────────────────────────────────
    prog_ok = sum(1 for n in PROGRAMS
                  if os.path.isfile(os.path.join(bindir, n))
                  and os.access(os.path.join(bindir, n), os.X_OK))
    check(prog_ok == len(PROGRAMS),
          f"bin/ 下 {len(PROGRAMS)} 个独立产物存在且可执行（{'/'.join(PROGRAMS)}）",
          f"仅 {prog_ok}/{len(PROGRAMS)} 个独立产物可用")

    # ── 7. 手册页 ───────────────────────────────────────────────────
    mans = sorted(os.listdir(man1)) if os.path.isdir(man1) else []
    check(len(mans) == 16 and "cdtool.1" in mans,
          f"share/man/man1 下 {len(mans)} 份手册页且含 cdtool.1",
          f"手册页数量/内容异常（{len(mans)} 项）")
    man_alias_ok = all(
        os.path.islink(os.path.join(man1, n + ".1"))
        and os.readlink(os.path.join(man1, n + ".1")) == "cdtool.1"
        for n in ALIASES)
    check(man_alias_ok, "10 个别名手册页均为指向 cdtool.1 的符号链接",
          "别名手册页不是指向 cdtool.1 的符号链接")

    # ── 8. 真实运行（argv[0] 分派 + 版本/用法路径）────────────────────
    runs = [
        (os.path.join(bindir, "cdplay"), "-V", "CDTOOL"),
        (main_exe, "-V", "CDTOOL"),
        (os.path.join(bindir, "cdctrl"), "-h", "cdctrl"),
        (os.path.join(bindir, "cdown"), "-V", "cdown"),
        (os.path.join(bindir, "cdtool2cddb"), "-h", "Usage"),
    ]
    for exe, flag, needle in runs:
        try:
            rc, out = run([exe, flag])
        except subprocess.TimeoutExpired:
            print(f"{FAIL} {os.path.basename(exe)} {flag} 超时")
            failures.append(f"{os.path.basename(exe)} {flag} 超时")
            continue
        check(rc == 0 and needle in out,
              f"真实运行 {os.path.basename(exe)} {flag} rc=0 且输出含 "
              f"{needle!r}",
              f"{os.path.basename(exe)} {flag} 异常（rc={rc}，"
              f"输出 {out[:120]!r}）")

    # ── 9. 如实记录 ─────────────────────────────────────────────────
    if os.path.exists(os.path.join(bindir, "cdtool")):
        print(f"{FAIL} bin/cdtool 意外存在（上游布局不在 bin/ 放主程序）")
        failures.append("bin/cdtool 意外存在")
    else:
        print(f"{NOTE} bin/ 下无 cdtool 入口属上游设计：主程序在 "
              f"lib/cdtool/cdtool，bin/ 的 10 个别名指向它")
    print(f"{NOTE} 上游无自动化测试套件（无 tests/、无 check 目标），"
          f"TOTAL=0 如实声明；本消费测试为其功能性替代验证")

    if failures:
        print(f"{FAIL} {len(failures)} 项检查失败")
        for item in failures:
            print(f"       - {item}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
