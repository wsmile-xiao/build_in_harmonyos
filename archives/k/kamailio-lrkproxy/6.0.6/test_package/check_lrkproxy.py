#!/usr/bin/env python3
"""kamailio-lrkproxy test_package — 产物结构校验（L1 消费者视角）。

lrkproxy.so 由 kamailio 二进制运行时 dlopen（loadmodule），且其功能语义
（LRK 媒体代理控制）需要运行中的 kamailio core + LRK 媒体代理实例，
无法在 CI 上做真实联机。故按产物结构做实质校验：
ELF 架构、模块注册与 ABI 导出符号（.dynsym 中 exports / module_version /
module_interface_ver / module_flags）、无宿主路径泄漏。
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
    module = os.environ["KAMAILIO_LRKPROXY_MODULE"]

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

    # 2) 模块核心符号：kamailio 运行时以 dlsym 解析 `exports`（模块注册结构）与
    #    `module_version`/`module_interface_ver`/`module_flags`（模块 ABI 全局量），
    #    故按 .dynsym 定义符号精确校验（非子串匹配），并抽样模块自有实现符号。
    #    注：`mod_register` 属 core 侧 API、`lrk_build` 非本模块符号，均不出现在制品中。
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    dyn_defined = set()
    if readelf:
        sym_out = subprocess.run([readelf, "--dyn-syms", module],
                                 capture_output=True, text=True).stdout
        for line in sym_out.splitlines():
            parts = line.split()
            # 形如: 33: 000000000004dcd8     8 OBJECT  GLOBAL DEFAULT   15 exports
            if len(parts) < 8 or parts[3] not in ("FUNC", "OBJECT"):
                continue
            if parts[4] in ("GLOBAL", "WEAK") and parts[6] != "UND":
                dyn_defined.add(parts[7].split("@")[0])
        check(bool(dyn_defined), "解析 .dynsym 定义符号表", f"{len(dyn_defined)} 个")
        for sym in ("exports", "module_version", "module_interface_ver", "module_flags",
                    "lrkproxy_hash_table_lookup", "insert_lrkp_node"):
            check(sym in dyn_defined, f"模块导出符号 {sym}")
    else:
        check(b"exports" in blob, "模块注册符号 exports（无 readelf 时退化为字符串标记）")
    check(b"lrkproxy" in blob, "模块名字符串标记 lrkproxy")

    # 3) 工具链侧复核（存在则执行，提供动态段附加证据）
    if readelf:
        out = subprocess.run([readelf, "-d", module],
                             capture_output=True, text=True).stdout
        # 交叉编译产物不得内嵌构建机路径（RPATH/RUNPATH 泄漏 = 目标机加载失败）
        check(not any(k in out for k in ("RPATH", "RUNPATH")),
              "动态段无 RPATH/RUNPATH", "clean")
        needed = [ln for ln in out.splitlines() if "NEEDED" in ln]
        # 零外部依赖模块：只允许 libc/libcompiler-runtime 级别的 NEEDED
        allowed = ("libc.so", "libc++.so", "libunwind", "ld-musl", "ld-android")
        unexpected = [ln.split("[")[-1].rstrip("] \n") for ln in needed
                      if not any(a in ln for a in allowed)]
        check(not unexpected, "NEEDED 仅 libc/运行时（零外部依赖确认）",
              ", ".join(needed) if needed else "none")
    else:
        print("[SKIP] 未找到 readelf/llvm-readelf，跳过动态段复核")

    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)} 项 — {FAILURES}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
