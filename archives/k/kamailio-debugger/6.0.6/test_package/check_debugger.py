#!/usr/bin/env python3
"""kamailio-debugger 产物检查（L1 结构层，test_package 调用）。

检查对象是打包产物 lib/kamailio/modules/debugger.so：
  1. 存在性与非空；
  2. ELF 头：魔数 / 64 位 / 小端 / ET_DYN（共享模块） / AArch64；
  3. 动态段：NEEDED 仅 libc（模块 LIBS= 为空，OpenSSL 等第三方库不应被引入）、无 RUNPATH/RPATH；
  4. 动态符号：core 插件 API 必须导出（kamailio loadmodule 依赖 exports/dbg_rpc 等），
     且不得出现 glibc 版本化符号（目标为 OHOS/musl）；
  5. 许可证文件 licenses/COPYING（GPL-2.0-or-later）随包分发。

只读检查；readelf/nm/llvm-* 任一可用即可，工具缺失时对应项输出 [skip] 而不误判失败。
环境变量：DEBUGGER_MODULE=debugger.so 绝对路径，DEBUGGER_PACKAGE_FOLDER=被测包目录。
"""
import os
import shutil
import struct
import subprocess
import sys

MODULE = os.environ.get("DEBUGGER_MODULE", "")
PKG = os.environ.get("DEBUGGER_PACKAGE_FOLDER", "")

PASS = 0
FAIL = 0
SKIP = 0


def check(cond, what):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("[ok]   " + what)
    else:
        FAIL += 1
        print("[FAIL] " + what)


def skip(what):
    global SKIP
    SKIP += 1
    print("[skip] " + what)


def run_tool(candidates, args):
    """返回 (工具路径, 输出) 或 (None, None)。"""
    for cand in candidates:
        path = cand if os.path.isabs(cand) else shutil.which(cand)
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            try:
                out = subprocess.run([path] + args, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, timeout=120)
            except Exception as exc:  # 工具异常不应让结构检查变成误判
                print("       (%s 执行失败: %s)" % (path, exc))
                continue
            if out.returncode == 0:
                return path, out.stdout.decode("utf-8", "replace")
    return None, None


READELF = ["/data/service/hnp/bin/llvm-readelf", "llvm-readelf", "readelf"]
NM = ["/data/service/hnp/bin/llvm-nm", "llvm-nm", "nm"]

# core 插件必须导出的符号：kamailio 主程序据此完成模块注册与 RPC/命令挂载
REQUIRED_EXPORTS = [
    "exports",            # module_exports 描述符（loadmodule 第一入口）
    "mod_register",       # 模块注册钩子（kemi 输出）
    "dbg_rpc",            # RPC 方法表（dbg.bp/dbg.ls/... ）
    "dbg_cfg",            # cfg 组句柄
    "dbg_init_rpc",       # RPC 注册 API
    "dbg_init_bp_list",   # 断点表初始化 API
    "dbg_init_pid_list",  # 进程表初始化 API
    "dbg_init_mod_levels",  # 每模块日志级别表初始化 API
    "dbg_add_breakpoint",   # 断点添加 API
    "dbg_msgid_filter",     # 脚本回调（reset_msgid）
]


def main():
    print("== kamailio-debugger 产物结构检查 ==")
    print("module: %s" % MODULE)
    print("package: %s\n" % PKG)

    if not MODULE or not PKG:
        check(False, "环境变量 DEBUGGER_MODULE / DEBUGGER_PACKAGE_FOLDER 均已设置")
        return 1
    check(True, "环境变量 DEBUGGER_MODULE / DEBUGGER_PACKAGE_FOLDER 均已设置")

    if not os.path.isfile(MODULE):
        check(False, "debugger.so 存在：%s" % MODULE)
        return 1
    size = os.path.getsize(MODULE)
    check(size > 0, "debugger.so 存在且非空（%d bytes）" % size)

    # ── ELF 头 ──
    with open(MODULE, "rb") as fh:
        head = fh.read(64)
    check(head[:4] == b"\x7fELF", "ELF 魔数正确")
    check(len(head) == 64 and head[4] == 2, "ELFCLASS64（64 位目标）")
    check(len(head) == 64 and head[5] == 1, "ELFDATA2LSB（小端）")
    e_type, e_machine = struct.unpack("<HH", head[16:20])
    check(e_type == 3, "e_type == ET_DYN(3)（共享模块，实际 %d）" % e_type)
    check(e_machine == 0xB7, "e_machine == AArch64(0xB7)（实际 0x%x）" % e_machine)

    # ── 动态段：NEEDED / RUNPATH / RPATH ──
    tool, dyn = run_tool(READELF, ["-d", MODULE])
    if tool is None:
        skip("llvm-readelf/readelf 不可用，跳过动态段检查")
    else:
        needed = []
        for raw in dyn.splitlines():
            line = raw.strip()
            if "(NEEDED)" in line and "[" in line:
                needed.append(line.split("[")[1].split("]")[0])
        print("       NEEDED=%s" % needed)
        check(all("libc" in n or "libdl" in n for n in needed),
              "NEEDED 仅含 libc/libdl（模块无第三方库依赖，实际 %s）" % needed)
        check(not any("(RPATH)" in l or "(RUNPATH)" in l for l in dyn.splitlines()),
              "无 RPATH/RUNPATH（不把构建机路径带入产物）")

    # ── 动态符号 ──
    tool, syms = run_tool(NM, ["-D", "--defined-only", MODULE])
    if tool is None:
        tool, syms = run_tool(READELF, ["--dyn-syms", MODULE])
    if tool is None:
        skip("nm/readelf 不可用，跳过动态符号检查")
    else:
        missing = [s for s in REQUIRED_EXPORTS if s not in syms]
        check(not missing, "core 插件 API 全部导出（缺失: %s）" % (missing or "无"))
        check("GLIBC_" not in syms, "无 glibc 版本化符号（目标为 OHOS/musl）")

    # ── 许可证 ──
    lic = os.path.join(PKG, "licenses", "COPYING")
    check(os.path.isfile(lic), "licenses/COPYING 随包分发")
    if os.path.isfile(lic):
        with open(lic, "rb") as fh:
            txt = fh.read(4096).decode("utf-8", "replace")
        check("GNU GENERAL PUBLIC LICENSE" in txt.upper(),
              "COPYING 为 GNU GPL 正文（模块 license=GPL-2.0-or-later）")

    print("\n== 结果：%d passed, %d failed, %d skipped ==" % (PASS, FAIL, SKIP))
    print("== %s ==" % ("ALL CHECKS PASSED" if FAIL == 0 else "CHECKS FAILED"))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
