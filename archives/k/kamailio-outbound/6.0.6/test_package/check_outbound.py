#!/usr/bin/env python3
"""outbound.so 打包产物校验（L1 消费者视角）。

模块 .so 由 kamailio 二进制运行时 dlopen（交叉编译产物无法在构建机直接执行，
且 outbound 的会话/注册流程需要运行中的 kamailio 与 SIP 对端），故按产物结构做实质校验：
ELF 架构、模块 API 导出符号、OpenSSL 静态吸收、musl/clang 无 glibc 版本化符号、
许可证文件与 RPATH/RUNPATH 宿主路径泄漏。
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
    module = os.environ["OUTBOUND_MODULE"]
    pkg = os.environ["OUTBOUND_PACKAGE_FOLDER"]

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

    # 2) 模块 API 导出符号
    #    exports 是 kamailio 模块向 core 注册的导出描述符（src/core/sr_module.h）；
    #    use_outbound 是 outbound 模块暴露的配置/路由函数，outbound_cfg 为模块配置结构。
    for marker in (b"exports", b"use_outbound", b"outbound_cfg"):
        check(marker in blob, f"模块导出符号 {marker.decode()}")

    # 3) musl/clang 交叉编译：不得出现 glibc 版本化符号（GLIBC_2.x）
    check(b"GLIBC_" not in blob, "无 glibc 版本化符号（musl/clang 交叉编译）")

    # 4) R26：OpenSSL 静态吸收（不引入 libssl/libcrypto 动态依赖串）
    check(b"libssl.so" not in blob and b"libcrypto.so" not in blob,
          "OpenSSL 静态吸收（无 libssl.so/libcrypto.so 依赖串）")

    # 5) 许可证文件随包安装
    license_file = os.path.join(pkg, "licenses", "COPYING")
    check(os.path.isfile(license_file), "licenses/COPYING 存在", license_file)

    # 6) 工具链侧复核（存在则执行，提供动态段附加证据）
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    if readelf:
        out = subprocess.run([readelf, "-d", module], capture_output=True, text=True).stdout
        needed = [ln.split("[")[-1].rstrip("] \n") for ln in out.splitlines() if "NEEDED" in ln]
        check(all(n.startswith("libc.so") for n in needed),
              "动态段 NEEDED 仅 libc.so", ", ".join(needed) or "无")
        # 交叉编译产物不得内嵌构建机路径（RPATH/RUNPATH 泄漏 = 目标机加载失败）
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
