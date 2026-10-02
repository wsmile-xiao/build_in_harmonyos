#!/usr/bin/env python3
"""kamailio 主二进制打包产物校验（L1 消费者视角）。

完整 SIP 服务运行需配置与运行环境，故按产物结构做实质校验：ELF 架构/PIE、
版本标识、依赖面（musl 下 NEEDED 仅 libc.so，pthread/m/dl 已并入）、
无 RPATH/RUNPATH 泄漏、许可证随包。
"""
import os
import re
import shutil
import subprocess
import sys

FAILURES = []


def check(cond, label, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(label)


def main():
    binary = os.environ["KAMAILIO_BINARY"]
    pkg = os.environ["KAMAILIO_PACKAGE_FOLDER"]

    with open(binary, "rb") as fh:
        blob = fh.read()
    print(f"artifact: {binary} ({len(blob)} bytes)")

    # 1) ELF 结构：64 位 / ET_DYN（PIE，按共享对象构建供运行时 dlopen 模块）/ AArch64
    check(blob[:4] == b"\x7fELF", "ELF 魔数")
    check(blob[4] == 2, "ELFCLASS64", f"ei_class={blob[4]}")
    e_type = int.from_bytes(blob[16:18], "little")
    check(e_type == 3, "ET_DYN（PIE 可执行）", f"e_type={e_type}")
    e_machine = int.from_bytes(blob[18:20], "little")
    check(e_machine == 0xB7, "e_machine=AArch64", f"e_machine={e_machine}")

    # 2) 版本标识与 core 特征符号（主二进制内嵌版本号；SIP 核心 API 符号，
    #    均已在 6.1.3 构建产物中实测存在）
    check(b"kamailio 6.1.3" in blob, "版本标识 kamailio 6.1.3")
    for marker in (b"mod_register", b"core_cfg", b"sip_msg", b"loadmodule"):
        check(marker in blob, f"core 特征标记 {marker.decode()}")

    # 3) 许可证随包安装
    check(os.path.isfile(os.path.join(pkg, "licenses", "COPYING")), "licenses/COPYING 存在")

    # 4) 工具链侧复核（存在则执行，提供动态段附加证据）
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    if readelf:
        out = subprocess.run([readelf, "-d", binary], capture_output=True, text=True).stdout
        needed = []
        for ln in out.splitlines():
            if "NEEDED" in ln:
                m = re.search(r"\[([^\]]+)\]", ln)
                if m:
                    needed.append(m.group(1))
        # 空集守卫：解析不到任何 NEEDED 行 = 动态段异常，必须判负而非空集真
        check(bool(needed) and all(n == "libc.so" for n in needed),
              "依赖面仅 libc.so（musl 内置 pthread/m/dl）", ", ".join(needed) or "none")
        # 交叉编译产物不得内嵌构建机路径（RPATH/RUNPATH 泄漏 = 目标机加载失败）
        check(not any("(RPATH)" in ln or "(RUNPATH)" in ln for ln in out.splitlines()),
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
