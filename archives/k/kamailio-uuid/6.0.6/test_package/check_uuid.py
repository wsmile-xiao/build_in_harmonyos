#!/usr/bin/env python3
"""uuid.so 打包产物校验（L1 消费者视角）。

模块 .so 由 kamailio 二进制运行时 loadmodule 加载（$u(...) 伪变量在 SIP 配置
脚本中求值，需运行中的 kamailio 进程），故按产物结构做实质校验：ELF 架构、
libuuid 静态链入证据、模块 API 导出符号、许可证随包与宿主路径泄漏检查。
"""
import os
import shutil
import subprocess
import sys

FAILURES = []

# libuuid 真实 API 集合（util-linux uuid/uuid.h 导出），用于区分 libuuid 符号
# 与 kamailio core 侧同名前缀符号（后者由宿主 kamailio 进程 dlopen 时解析）
LIBUUID_API = (
    "uuid_generate", "uuid_generate_random", "uuid_generate_time",
    "uuid_generate_time_safe", "uuid_unparse", "uuid_unparse_lower",
    "uuid_unparse_upper", "uuid_parse", "uuid_clear", "uuid_copy",
    "uuid_compare", "uuid_is_null", "uuid_type", "uuid_variant", "uuid_time",
)


def check(cond, label, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(label)


def env(name):
    """取环境变量；缺失时登记可读失败而不是抛 KeyError。"""
    val = os.environ.get(name)
    if not val:
        check(False, f"环境变量 {name}",
              "未注入（检查 test_package/conanfile.py 的 Environment 定义）")
    return val


def bail():
    """提前退出：打印失败汇总，保持退出码语义为 1（可判定的失败）。"""
    print(f"\nFAILED: {len(FAILURES)} 项 — {FAILURES}")
    return 1


def main():
    module = env("KAMAILIO_UUID_MODULE")
    pkg = env("KAMAILIO_UUID_PACKAGE_FOLDER")
    if FAILURES:
        return bail()

    if not os.path.isfile(module):
        check(False, "产物存在", f"{module} 不存在")
        return bail()

    with open(module, "rb") as fh:
        blob = fh.read()
    print(f"artifact: {module} ({len(blob)} bytes)")

    # ELF64 头固定 64 字节。短于此的截断/空产物无法判定字段，先失败退出，
    # 避免 blob[4] 越界抛 IndexError 把"产物损坏"掩盖成"脚本崩溃"
    if len(blob) < 64:
        check(False, "ELF 头长度", f"{len(blob)} 字节 < 64 字节（截断或空产物）")
        return bail()

    # 1) ELF 结构：64 位 / 可重定位共享对象 / AArch64
    check(blob[:4] == b"\x7fELF", "ELF 魔数")
    check(blob[4] == 2, "ELFCLASS64", f"ei_class={blob[4]}")
    e_type = int.from_bytes(blob[16:18], "little")
    check(e_type == 3, "ET_DYN（共享对象）", f"e_type={e_type}")
    e_machine = int.from_bytes(blob[18:20], "little")
    check(e_machine == 0xB7, "e_machine=AArch64", f"e_machine={e_machine}")

    # 2) libuuid 静态链入证据：uuid_generate/uuid_unparse_lower/uuid_clear 是模块
    #    生成与格式化 UUID 必用的 libuuid API（uuid_mod.c 直接调用）；
    #    mod_register 是 kamailio 模块入口符号（未被静态链接丢弃 = 模块可被加载）
    for marker in (b"uuid_generate", b"uuid_unparse_lower", b"uuid_clear",
                   b"mod_register"):
        check(marker in blob, f"符号标记 {marker.decode()}")

    # 3) 许可证随包安装
    check(os.path.isfile(os.path.join(pkg, "licenses", "COPYING")), "licenses/COPYING 存在")

    # 4) 工具链侧复核（存在则执行，提供动态段/符号表附加证据）
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    if readelf:
        proc = subprocess.run([readelf, "-d", module], capture_output=True, text=True)
        if proc.returncode != 0:
            # 工具自身失败时不能按"NEEDED 为空"放过（那会把读不到当成没依赖）
            check(False, "动态段读取 (readelf -d)",
                  f"exit={proc.returncode} {(proc.stderr or '').strip()[:200]}")
        else:
            out = proc.stdout
            needed = [ln.split("[")[-1].rstrip("] \n") for ln in out.splitlines() if "NEEDED" in ln]
            check(all("libuuid" not in n for n in needed),
                  "libuuid 静态链入（NEEDED 无 libuuid）", ", ".join(needed) or "none")
            # 交叉编译产物不得内嵌构建机路径（RPATH/RUNPATH 泄漏 = 目标机加载失败）
            check(not any(k in out for k in ("RPATH", "RUNPATH")),
                  "动态段无 RPATH/RUNPATH", "clean")
    else:
        print("[SKIP] 未找到 readelf/llvm-readelf，跳过动态段复核")

    nm = shutil.which("llvm-nm") or shutil.which("nm")
    if nm:
        proc = subprocess.run([nm, "-u", module], capture_output=True, text=True)
        if proc.returncode != 0:
            # 同上：nm 失败 ≠ 无未解析符号，必须判失败而非静默通过
            check(False, "符号表读取 (nm -u)",
                  f"exit={proc.returncode} {(proc.stderr or '').strip()[:200]}")
        else:
            unresolved = set()
            for ln in proc.stdout.splitlines():
                ln = ln.strip()
                # 过滤 nm 诊断行（如 "nm: <file>: file format not recognized"），
                # 其尾 token 不是符号，混入会造出假失败
                if not ln or ln.startswith("nm:") or ":" in ln:
                    continue
                unresolved.add(ln.split()[-1])
            # 只对 libuuid 真 API 判未解析：模块 .so 由 kamailio 二进制 dlopen 加载，
            # core 侧符号（如 sruid_uuid_api_set 等 *uuid* 命名的 core API）本就应由
            # 宿主 kamailio 进程解析，不算依赖缺失
            leaked = sorted(unresolved & set(LIBUUID_API))
            check(not leaked, "libuuid API 无未解析符号（已静态并入）",
                  ", ".join(leaked) or "none")
    else:
        print("[SKIP] 未找到 nm/llvm-nm，跳过符号表复核")

    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)} 项 — {FAILURES}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
