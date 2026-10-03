#!/usr/bin/env python3
"""ktimer 消费者冒烟测试（L0c 测试源文件）。

上游 ktimer 26.04.0 无任何测试用例（无 tests/ 目录、CMakeLists 无 add_test /
enable_testing / ecm_add_tests，MANIFEST 如实申报 0）。本脚本真实执行安装后的
ktimer 二进制：`ktimer --version` 由 KAboutData::processCommandLine 处理
（在 KDBusService、托盘 KStatusNotifierItem、主窗口创建之前），打印版本并以 0
退出 —— 验证可执行文件存在、Qt6/KF6/Qt6DBus 共享库依赖经 conanrun env
（PATH / LD_LIBRARY_PATH / QT_PLUGIN_PATH）完整解析；任何依赖或平台问题都会
反映为非 0 退出码或 subprocess 超时 → FAIL（如实报告，不隐藏）。

超时用 subprocess.run(timeout=60) 兜底（OHOS worker 无 shell timeout 命令，
CI #60869 实测 [Errno 2]）。QT_QPA_PLATFORM=offscreen 由调用方注入。
"""
import os
import struct
import subprocess
import sys

VERSION = "26.04.0"
BINARY = "ktimer"


def _readelf_dynamic(path):
    """极简 ELF64 .dynamic 解析：打印 DT_NEEDED/DT_RPATH/DT_RUNPATH。
    CI #60984 实测 conanrun PATH 无 llvm-readelf，改用纯 python 直读。"""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        print("[readelf] 无法读取 %s: %s" % (path, exc))
        return
    if data[:4] != b"\x7fELF":
        print("[readelf] 非 ELF 文件: %s" % path)
        return
    e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", data, 0x36)[0]
    e_phnum = struct.unpack_from("<H", data, 0x38)[0]
    dyn = None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        if struct.unpack_from("<I", data, off)[0] == 2:  # PT_DYNAMIC
            dyn = (struct.unpack_from("<Q", data, off + 8)[0],
                   struct.unpack_from("<Q", data, off + 16)[0])
            break
    if not dyn:
        print("[readelf] 无 PT_DYNAMIC 段")
        return
    doff, dsz = dyn
    tags = {1: "NEEDED", 5: "STRTAB", 15: "RPATH", 29: "RUNPATH"}
    names = {}
    for pos in range(doff, doff + dsz, 16):
        tag = struct.unpack_from("<Q", data, pos)[0]
        val = struct.unpack_from("<Q", data, pos + 8)[0]
        if tag == 0:
            break
        if tag in tags:
            names[tag] = val
    strtab = names.get(5)
    if strtab is None:
        print("[readelf] 无 DT_STRTAB")
        return
    for pos in range(doff, doff + dsz, 16):
        tag = struct.unpack_from("<Q", data, pos)[0]
        val = struct.unpack_from("<Q", data, pos + 8)[0]
        if tag == 0:
            break
        if tag in (1, 15, 29):
            end = data.find(b"\0", strtab + val)
            print("[readelf] %s %s" % (
                tags[tag], data[strtab + val:end].decode("utf-8", "replace")))


def main():
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    # 显式二进制路径：test_package 经 KTIMER_BIN 传入（CI #60877 实测
    # conanrun 的 PATH 不含被测包 bin 目录，裸名查找报 [Errno 2]）；
    # 未传时退化为裸名，便于本地开发直接运行。
    bin_path = os.environ.get("KTIMER_BIN") or BINARY

    # 诊断：回显 DT_RPATH/DT_NEEDED，供 CI 日志核实 RPATH 落位。
    _readelf_dynamic(bin_path)

    try:
        proc = subprocess.run(
            [bin_path, "--version"],
            env=env, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        print("[FAIL] %s --version 无法启动: %s" % (bin_path, exc))
        return 1

    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        print("[FAIL] ktimer --version 退出码 %d" % proc.returncode)
        print(out)
        return 1
    if VERSION not in out:
        print("[FAIL] 输出未含版本号 %s" % VERSION)
        print(out)
        return 1
    if BINARY not in out.lower():
        print("[FAIL] 输出未含程序名 %s" % BINARY)
        print(out)
        return 1
    print("[PASS] ktimer --version 退出码 0，输出: %s" % out.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
