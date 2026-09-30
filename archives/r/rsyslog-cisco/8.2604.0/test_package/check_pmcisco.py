#!/usr/bin/env python3
"""pmciscoios.so / pmcisconames.so 打包产物校验（L1 消费者视角）。

两个模块都是 rsyslog *可加载模块*：rsyslogd 运行时 dlopen 后经
objGetObjInterface/queryEtryPt 取入口，构建机直接执行需要完整 rsyslogd 与
parser 框架，故按产物结构做实质校验：ELF 架构、模块入口导出符号（modInit）、
parser 名称字符串（GetParserName 返回值）、musl/clang 无 glibc 版本化符号、
无 zlib/libestr/libfastjson 动态依赖串（配方显式清空 $(LIBS) 的目的）、
NEEDED 仅 libc 且无 RPATH/RUNPATH、许可证随包安装、模块目录内容。

运行期行为（真实 Parser 入口调用链）由同目录 test_pmcisco_e2e.c 覆盖。
"""
import os
import shutil
import subprocess
import sys

FAILURES = []
MODULES = ("pmciscoios.so", "pmcisconames.so")
# GetParserName() 的返回值（各模块 PARSER_NAME 宏），交叉编译产物中为字面量
PARSER_NAMES = (b"rsyslog.ciscoios\x00", b"rsyslog.cisconames\x00")


def check(cond, label, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(label)


def section(blob, shoff, shentsize, shnum, shstrndx, name):
    """返回段名 == name 的 (offset, size)，无则 None。"""
    for i in range(shnum):
        base = shoff + i * shentsize
        sh_name = int.from_bytes(blob[base:base + 4], "little")
        sh_offset = int.from_bytes(blob[base + 24:base + 32], "little")
        sh_size = int.from_bytes(blob[base + 32:base + 40], "little")
        strbase = shoff + shstrndx * shentsize
        str_off = int.from_bytes(blob[strbase + 24:strbase + 32], "little")
        raw = blob[str_off + sh_name:str_off + sh_name + 64]
        if raw.split(b"\x00", 1)[0].decode("latin1") == name:
            return sh_offset, sh_size
    return None


def find_readelf():
    for cand in ("llvm-readelf", "readelf", "/data/service/hnp/bin/readelf"):
        path = shutil.which(cand) if "/" not in cand else (cand if os.path.isfile(cand) else None)
        if path:
            return path
    return None


def check_module(module, parser_names):
    with open(module, "rb") as fh:
        blob = fh.read()
    base = os.path.basename(module)
    print(f"\n=== {base}: {module} ({len(blob)} bytes) ===")

    # 1) ELF 结构：64 位 / 可重定位共享对象 / AArch64
    check(blob[:4] == b"\x7fELF", f"{base}: ELF 魔数")
    check(blob[4] == 2, f"{base}: ELFCLASS64", f"ei_class={blob[4]}")
    e_type = int.from_bytes(blob[16:18], "little")
    check(e_type == 3, f"{base}: ET_DYN（共享对象）", f"e_type={e_type}")
    e_machine = int.from_bytes(blob[18:20], "little")
    check(e_machine == 0xB7, f"{base}: e_machine=AArch64", f"e_machine={e_machine}")

    # 2) 模块入口导出符号：modInit（module-template.h 展开），rsyslogd 经
    #    dlsym 获取；_init/_fini 为可加载模块常规入口。
    shoff = int.from_bytes(blob[40:48], "little")
    shentsize = int.from_bytes(blob[58:60], "little")
    shnum = int.from_bytes(blob[60:62], "little")
    shstrndx = int.from_bytes(blob[62:64], "little")
    dynstr = section(blob, shoff, shentsize, shnum, shstrndx, ".dynstr")
    check(dynstr is not None, f"{base}: 存在 .dynstr 段")
    if dynstr is not None:
        off, size = dynstr
        names = blob[off:off + size]
        for symbol in (b"modInit", b"_init", b"_fini"):
            check(f"{symbol.decode()}\x00".encode() in names,
                  f"{base}: .dynstr 导出符号 {symbol.decode()}")
        # 3) Parser 名称：GetParserName() 返回 PARSER_NAME 字面量，是模块
        #    在 parser 框架中注册的名字（rsyslog.conf 里 parser= 引用它）。
        for pname in parser_names:
            check(pname in blob, f"{base}: PARSER_NAME 字面量 {pname.decode().rstrip(chr(0))}")

    # 4) musl/clang 交叉编译：不得出现 glibc 版本化符号（GLIBC_2.x）
    check(b"GLIBC_" not in blob, f"{base}: 无 glibc 版本化符号（musl/clang 交叉编译）")

    # 5) 配方显式 `make ... LIBS=` 的目的：模块不得引入 zlib 动态依赖串
    #    （目标机无 libz.so.1 时 loadmodule 会失败），也不得依赖
    #    libestr/libfastjson（模块只经 rsyslog 头文件使用其类型，不链接它们）。
    for unwanted in (b"libz.so", b"libestr.so", b"libfastjson.so"):
        check(unwanted not in blob, f"{base}: 无动态依赖串 {unwanted.decode()}")

    # 6) 加载期依赖面（纯 ELF 字节自检，不依赖外部工具）：可加载模块只应依赖
    #    libc，且不得携带 RPATH/RUNPATH —— 这两者才是"构建机路径进入加载过程"
    #    从而在目标机失败的形式。构建机绝对路径字符串（assert/__FILE__ 记录的
    #    源码路径，交叉编译产物中必然存在）不参与加载，不属缺陷。
    dynamic = section(blob, shoff, shentsize, shnum, shstrndx, ".dynamic")
    check(dynamic is not None, f"{base}: 存在 .dynamic 段")
    needed, rpaths = [], []
    if dynamic is not None and dynstr is not None:
        doff, dsize = dynamic
        soff, _ssize = dynstr
        for i in range(dsize // 16):
            pos = doff + i * 16
            tag = int.from_bytes(blob[pos:pos + 8], "little")
            val = int.from_bytes(blob[pos + 8:pos + 16], "little")
            if tag == 1:  # DT_NEEDED
                end = blob.index(b"\x00", soff + val)
                needed.append(blob[soff + val:end].decode("latin1"))
            elif tag in (15, 29):  # DT_RPATH / DT_RUNPATH
                end = blob.index(b"\x00", soff + val)
                rpaths.append(blob[soff + val:end].decode("latin1"))
    check(bool(needed) and all(n.startswith("libc.so") for n in needed),
          f"{base}: DT_NEEDED 仅 libc.so", ", ".join(needed) or "无")
    check(not rpaths, f"{base}: 无 DT_RPATH/DT_RUNPATH", ", ".join(rpaths) or "clean")


def main():
    pkg = os.environ["PMCISCO_PACKAGE_FOLDER"]
    moddir = os.path.join(pkg, "lib", "rsyslog")

    # 7) 模块目录内容：仅两个目标模块
    present = sorted(os.listdir(moddir)) if os.path.isdir(moddir) else []
    check(present == sorted(MODULES), "lib/rsyslog 仅含两个目标模块", ", ".join(present))

    for idx, name in enumerate(MODULES):
        module = os.path.join(moddir, name)
        if not os.path.isfile(module):
            check(False, f"{name}: 产物存在", module)
            continue
        check_module(module, (PARSER_NAMES[idx],))

    # 8) 许可证随包安装
    license_file = os.path.join(pkg, "licenses", "COPYING")
    check(os.path.isfile(license_file), "licenses/COPYING 存在", license_file)

    # 9) 工具链侧复核（存在则执行，提供动态段附加证据）
    readelf = find_readelf()
    if readelf:
        for name in MODULES:
            module = os.path.join(moddir, name)
            if not os.path.isfile(module):
                continue
            out = subprocess.run([readelf, "-d", module], capture_output=True, text=True).stdout
            needed = [ln.split("[")[-1].rstrip("] \n") for ln in out.splitlines() if "NEEDED" in ln]
            check(all(n.startswith("libc.so") for n in needed),
                  f"{name}: 动态段 NEEDED 仅 libc.so", ", ".join(needed) or "无")
            check(not any(k in out for k in ("RPATH", "RUNPATH")),
                  f"{name}: 动态段无 RPATH/RUNPATH", "clean")
    else:
        print("[SKIP] 未找到 readelf/llvm-readelf，跳过动态段复核")

    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)} 项 — {FAILURES}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
