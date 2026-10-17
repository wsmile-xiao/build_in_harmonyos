#!/usr/bin/env python3
"""db_unixodbc.so 打包产物校验（L1 消费者视角）。

模块 .so 由 kamailio 二进制运行时 dlopen（且 db_unixodbc 是 SQL 连接器，
真正连库需要运行中的 kamailio + 可用 ODBC 数据源），故按产物结构做实质校验：
ELF 架构、unixODBC 动态依赖、模块 API 导出符号、许可证文件与宿主路径泄漏检查。
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
    module = os.environ["DB_UNIXODBC_MODULE"]
    pkg = os.environ["DB_UNIXODBC_PACKAGE_FOLDER"]

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

    # 2) unixODBC 动态依赖与模块 API 符号
    #    db_bind_api 是 db_unixodbc 向 kamailio core 注册的 DB 连接器 API（见 db_unixodbc.c exports）
    for marker in (b"libodbc.so.2", b"db_bind_api", b"db_unixodbc"):
        check(marker in blob, f"动态段/符号标记 {marker.decode()}")

    # 3) 许可证文件随包安装
    license_file = os.path.join(pkg, "licenses", "COPYING")
    check(os.path.isfile(license_file), "licenses/COPYING 存在", license_file)

    # 4) 工具链侧复核（存在则执行，提供动态段附加证据）
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    if readelf:
        out = subprocess.run([readelf, "-d", module], capture_output=True, text=True).stdout
        needed = [ln.split("[")[-1].rstrip("] \n") for ln in out.splitlines() if "NEEDED" in ln]
        check(any("libodbc.so.2" in n for n in needed),
              "动态段 NEEDED 含 libodbc.so.2", ", ".join(needed))
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
