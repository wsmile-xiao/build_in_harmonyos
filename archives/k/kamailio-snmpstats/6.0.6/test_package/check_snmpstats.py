#!/usr/bin/env python3
"""snmpstats.so 打包产物校验（L1 消费者视角）。

模块 .so 由 kamailio 二进制运行时 dlopen（交叉编译产物无法在构建机直接执行），
故按产物结构做实质校验：ELF 架构、AgentX 依赖、模块导出/数据标记、MIB 数据文件。
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


def main():
    module = os.environ["SNMPSTATS_MODULE"]
    pkg = os.environ["SNMPSTATS_PACKAGE_FOLDER"]

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

    # 2) 动态依赖与模块符号（snmpstats 作为 AgentX 子代理必须依赖 agent 系库）
    for marker in (b"libnetsnmpagent.so.40", b"libnetsnmpmibs.so.40",
                   b"register_with_master_agent", b"snmpstats"):
        check(marker in blob, f"动态段/符号标记 {marker.decode()}")

    # 3) KAMAILIO MIB 数据文件随包安装
    mibs_dir = os.path.join(pkg, "share", "snmp", "mibs")
    mibs = sorted(os.listdir(mibs_dir)) if os.path.isdir(mibs_dir) else []
    check(len(mibs) == 5, "KAMAILIO MIB 文件 5 个", ", ".join(mibs) or "无")

    # 4) 工具链侧复核（存在则执行，提供动态段附加证据）
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    if readelf:
        out = subprocess.run([readelf, "-d", module], capture_output=True, text=True).stdout
        needed = [ln.split("[")[-1].rstrip("] \n") for ln in out.splitlines() if "NEEDED" in ln]
        check(any("libnetsnmpagent" in n for n in needed),
              "动态段 NEEDED 含 libnetsnmpagent", ", ".join(needed))
    else:
        print("[SKIP] 未找到 readelf/llvm-readelf，跳过动态段复核")

    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)} 项 — {FAILURES}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
