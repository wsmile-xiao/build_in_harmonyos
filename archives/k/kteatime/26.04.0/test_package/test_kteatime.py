#!/usr/bin/env python3
"""kteatime 消费者冒烟测试（L0c 测试源文件）。

上游 kteatime 26.04.0 无任何测试用例（无 tests/ 目录、CMakeLists 无 test
目标，MANIFEST 如实申报 0）。本脚本为适配后补全的 smoke test：真实执行
安装后的 kteatime 二进制（--version 经 KAboutData 打印版本并以 0 退出），
验证可执行文件存在、Qt6/KF6 共享库依赖经 conanrun env（PATH /
LD_LIBRARY_PATH）完整解析；任何依赖/平台问题都会反映为非 0 退出码或
subprocess 超时被杀 → FAIL（如实报告，不隐藏）。不用 shell 的 timeout
命令（OHOS worker 无此命令，CI #60869 实测 [Errno 2]），超时由
subprocess.run(timeout=60) 兜底。

QT_QPA_PLATFORM=offscreen：Qt6 在无显示环境下可用（qtbase 配方自身测试
同款设置）。
"""
import os
import struct
import subprocess
import sys


def _readelf_dynamic(path):
    """极简 ELF64 小端 .dynamic 解析：打印 DT_NEEDED/DT_RPATH/DT_RUNPATH。
    CI #60984 实测 conanrun env 的 PATH 无 llvm-readelf，改用纯 python
    （struct 直读，无外部工具依赖）。"""
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
    # 显式二进制路径（test_package 经 KTEATIME_BIN 传入，CI #60877 实测
    # conanrun PATH 不含被测试包 bin 目录，裸名查找 [Errno 2]）；未传时
    # 退化为裸名（本地开发可直接运行）。
    bin_path = os.environ.get("KTEATIME_BIN") or "kteatime"
    # 诊断：回显二进制 DT_RPATH/DT_NEEDED（纯 python 解析，不依赖
    # llvm-readelf），供 CI 日志核实 RPATH 落位（#60939 根因=主二进制
    # auto-RPATH 缺传递依赖目录，加载器落入 KF6 .so 自身坏 RPATH：
    # .conan2 过期绝对路径 / ../../bin 相对路径）。
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
        print("[FAIL] kteatime --version 退出码 %d" % proc.returncode)
        print(out)
        return 1
    if "kteatime" not in out.lower():
        print("[FAIL] 输出未含 kteatime 版本信息")
        print(out)
        return 1
    print("[PASS] kteatime --version 退出码 0，输出: %s" % out.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
