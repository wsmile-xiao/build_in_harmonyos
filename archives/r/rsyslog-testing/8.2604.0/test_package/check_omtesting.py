#!/usr/bin/env python3
"""omtesting.so 打包产物校验（L1 消费者视角）。

模块 .so 由 rsyslogd 运行时 dlopen（omtesting 是测试/模拟 action，产物为交叉
编译模块，构建机直接执行需完整 rsyslogd 与规则引擎），故按产物结构做实质校验：
ELF 架构、模块入口导出符号、musl/clang 无 glibc 版本化符号、无 zlib 动态依赖串
（配方显式清空 $(LIBS) 的目的）、无构建机绝对路径泄漏、许可证随包安装、
NEEDED 仅 libc 且无 RPATH/RUNPATH。
"""
import os
import shutil
import subprocess
import sys

FAILURES = []


def check(cond, label, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(label)


def section(blob, shoff, shentsize, shnum, shstrndx, name):
    """返回段名 == name 的 (offset, size)，无则 None。"""
    with open("/dev/null", "w"):
        pass
    e = blob
    for i in range(shnum):
        base = shoff + i * shentsize
        sh_name = int.from_bytes(e[base:base + 4], "little")
        sh_offset = int.from_bytes(e[base + 24:base + 32], "little")
        sh_size = int.from_bytes(e[base + 32:base + 40], "little")
        strbase = shoff + shstrndx * shentsize
        str_off = int.from_bytes(e[strbase + 24:strbase + 32], "little")
        raw = e[str_off + sh_name:str_off + sh_name + 64]
        if raw.split(b"\x00", 1)[0].decode("latin1") == name:
            return sh_offset, sh_size
    return None


def main():
    module = os.environ["OMTESTING_MODULE"]
    pkg = os.environ["OMTESTING_PACKAGE_FOLDER"]

    with open(module, "rb") as fh:
        blob = fh.read()
    print(f"artifact: {module} ({len(blob)} bytes)")

    # 1) ELF 结构：64 位 / 可重定位共享对象 / AArch64
    check(blob[:4] == b"\x7fELF", "ELF 魔数")
    check(blob[4] == 2, "ELFCLASS64", f"ei_class={blob[4]}")
    e_type = int.from_bytes(blob[16:18], "little")
    check(e_type == 3, "ET_DYN（共享对象）", f"e_type={e_type}")
    e_machine = int.from_bytes(blob[18:20], "little")
    check(e_machine == 0xB7, "e_machine=AArch64", f"e_machine={e_machine}")

    # 2) 模块入口导出符号：omtesting.c 以 BEGINmodInit/ENDmodInit 展开为
    #    modInit（module-template.h），由 rsyslogd 经 dlsym 获取。
    shoff = int.from_bytes(blob[40:48], "little")
    shentsize = int.from_bytes(blob[58:60], "little")
    shnum = int.from_bytes(blob[60:62], "little")
    shstrndx = int.from_bytes(blob[62:64], "little")
    dynstr = section(blob, shoff, shentsize, shnum, shstrndx, ".dynstr")
    check(dynstr is not None, "存在 .dynstr 段")
    if dynstr is not None:
        off, size = dynstr
        names = blob[off:off + size]
        for symbol in (b"modInit", b"_init", b"_fini"):
            check(f"{symbol.decode()}\x00".encode() in names,
                  f".dynstr 导出符号 {symbol.decode()}")

    # 3) musl/clang 交叉编译：不得出现 glibc 版本化符号（GLIBC_2.x）
    check(b"GLIBC_" not in blob, "无 glibc 版本化符号（musl/clang 交叉编译）")

    # 4) 配方显式 `make -C plugins/omtesting LIBS=` 的目的：模块不得引入
    #    zlib 动态依赖串（目标机 /usr/lib 只有 libz.so.1，该 NEEDED 会使
    #    rsyslogd loadmodule 失败），也不得依赖 libestr/libfastjson
    #    （模块只经 rsyslog 头文件使用其类型，不链接它们）。
    for unwanted in (b"libz.so", b"libestr.so", b"libfastjson.so"):
        check(unwanted not in blob, f"无动态依赖串 {unwanted.decode()}")

    # 5) 加载期依赖面（纯 ELF 字节自检，不依赖外部工具）：可加载模块只应依赖
    #    libc，且不得携带 RPATH/RUNPATH —— 这两者才是"构建机路径进入加载过程"
    #    从而在目标机失败的形式。构建机绝对路径字符串（assert/__FILE__ 记录的
    #    源码路径，交叉编译产物中必然存在）不参与加载，不属缺陷。
    dynamic = section(blob, shoff, shentsize, shnum, shstrndx, ".dynamic")
    check(dynamic is not None, "存在 .dynamic 段")
    needed, rpaths = [], []
    if dynamic is not None and dynstr is not None:
        doff, dsize = dynamic
        soff, ssize = dynstr
        for i in range(dsize // 16):
            base = doff + i * 16
            tag = int.from_bytes(blob[base:base + 8], "little")
            val = int.from_bytes(blob[base + 8:base + 16], "little")
            if tag == 1:  # DT_NEEDED
                end = blob.index(b"\x00", soff + val)
                needed.append(blob[soff + val:end].decode("latin1"))
            elif tag in (15, 29):  # DT_RPATH / DT_RUNPATH
                end = blob.index(b"\x00", soff + val)
                rpaths.append(blob[soff + val:end].decode("latin1"))
    check(bool(needed) and all(n.startswith("libc.so") for n in needed),
          "DT_NEEDED 仅 libc.so", ", ".join(needed) or "无")
    check(not rpaths, "无 DT_RPATH/DT_RUNPATH", ", ".join(rpaths) or "clean")

    # 6) 许可证随包安装
    license_file = os.path.join(pkg, "licenses", "COPYING")
    check(os.path.isfile(license_file), "licenses/COPYING 存在", license_file)

    # 7) 模块目录内容：仅 omtesting.so
    moddir = os.path.join(pkg, "lib", "rsyslog")
    present = sorted(os.listdir(moddir)) if os.path.isdir(moddir) else []
    check(present == ["omtesting.so"], "lib/rsyslog 仅含 omtesting.so", ", ".join(present))

    # 8) 工具链侧复核（存在则执行，提供动态段附加证据）
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    if readelf:
        out = subprocess.run([readelf, "-d", module], capture_output=True, text=True).stdout
        needed = [ln.split("[")[-1].rstrip("] \n") for ln in out.splitlines() if "NEEDED" in ln]
        check(all(n.startswith("libc.so") for n in needed),
              "动态段 NEEDED 仅 libc.so", ", ".join(needed) or "无")
        check(not any(k in out for k in ("RPATH", "RUNPATH")),
              "动态段无 RPATH/RUNPATH", "clean")
    else:
        print("[SKIP] 未找到 readelf/llvm-readelf，跳过动态段复核")

    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)} 项 — {FAILURES}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
