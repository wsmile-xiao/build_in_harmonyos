#!/usr/bin/env python3
"""kamailio-slack 产物检查（test_package 调用）。

检查对象是打包产物 lib/kamailio/modules/slack.so，分两层：

  层 1 — 产物结构（只读）：
    1. 存在性与非空；
    2. ELF 头：魔数 / 64 位 / 小端 / ET_DYN（共享模块） / AArch64；
    3. 动态段：NEEDED 只允许 libc/libdl/libcurl（curl 由制品仓版本提供）、无 RUNPATH/RPATH；
    4. 动态符号：kamailio 核心 loadmodule() 按名解析的入口符号必须导出
       （exports / mod_register / module_version / module_flags / module_interface_ver），
       且不得出现 glibc 版本化符号；
    5. 许可证文件 licenses/COPYING（GPL-2.0-or-later）随包分发。

    符号集口径（本机实测 nm -D --defined-only 的导出集）：模块的 PARAM_USE_FUNC 回调
    `_slack_url_param` 不参与 dlopen 名字解析——它只经 mod_params[] 表内地址被核心调用，
    故不在（也不应在）dynsym 断言集中；把它列入必需导出会误判失败。

  层 2 — 消费者 E2E（真实执行，e2e_consumer.c）：
    以最小 kamailio 核心桩 dlopen 产物，按真实加载次序消费：exports 描述符 →
    cmds/params 表 → mod_register(KEMI) → mod_init(bind_http_client + pkg_malloc) →
    modparam slack_url 校验分支 → slack_send() 全链路（fixup → pv 渲染 → BODY_FMT 组包
    → http_client_query 投递 + 成功/失败分支）。

环境变量：
  SLACK_MODULE=slack.so 绝对路径，SLACK_PACKAGE_FOLDER=被测包目录
  SLACK_E2E_SRC=e2e_consumer.c 路径（缺省时层 2 跳过）
  SLACK_CC=交叉编译器（缺省 clang）
  SLACK_DEP_LIBDIRS=依赖库目录（冒号分隔，供 LD_LIBRARY_PATH 解析 libcurl.so）
  SLACK_BUILD_DIR=E2E 宿主编译输出目录（缺省临时目录）
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile

MODULE = os.environ.get("SLACK_MODULE", "")
PKG = os.environ.get("SLACK_PACKAGE_FOLDER", "")
E2E_SRC = os.environ.get("SLACK_E2E_SRC", "")
CC = os.environ.get("SLACK_CC", "clang")
DEP_LIBDIRS = os.environ.get("SLACK_DEP_LIBDIRS", "")
BUILD_DIR = os.environ.get("SLACK_BUILD_DIR", "")

L1_PASS = 0
L1_FAIL = 0
L1_SKIP = 0


def check(cond, what):
    global L1_PASS, L1_FAIL
    if cond:
        L1_PASS += 1
        print("[ok]   " + what)
    else:
        L1_FAIL += 1
        print("[FAIL] " + what)


def skip(what):
    global L1_SKIP
    L1_SKIP += 1
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

# loadmodule 时 kamailio 核心按名 dlsym 的入口符号（实测 dynsym 导出集）
REQUIRED_EXPORTS = [
    "exports",                 # module_exports 描述符（loadmodule 第一入口）
    "mod_register",            # 模块注册钩子（KEMI slack.slack_send）
    "module_version",          # MODULE_VERSION 宏导出的版本符号（版本兼容校验）
    "module_flags",            # 编译标志（核心输出用）
    "module_interface_ver",    # MODULE_INTERFACE_VER=4（接口版本校验）
]

# 允许出现的动态依赖：musl libc / libdl / 制品仓 curl（-lcurl 由模块 Makefile 引入）
ALLOWED_NEEDED = ("libc", "libdl", "libcurl")


def layer1_structure():
    print("== 层 1：产物结构检查 ==")
    print("module: %s" % MODULE)
    print("package: %s\n" % PKG)

    if not MODULE or not PKG:
        check(False, "环境变量 SLACK_MODULE / SLACK_PACKAGE_FOLDER 均已设置")
        return
    check(True, "环境变量 SLACK_MODULE / SLACK_PACKAGE_FOLDER 均已设置")

    if not os.path.isfile(MODULE):
        check(False, "slack.so 存在：%s" % MODULE)
        return
    size = os.path.getsize(MODULE)
    check(size > 0, "slack.so 存在且非空（%d bytes）" % size)

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
        check(all(any(a in n for a in ALLOWED_NEEDED) for n in needed),
              "NEEDED 仅含 libc/libdl/libcurl（实际 %s）" % needed)
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
        check(not missing, "loadmodule 入口符号全部导出（缺失: %s）" % (missing or "无"))
        check("GLIBC_" not in syms, "无 glibc 版本化符号（目标为 OHOS/musl）")

    # ── 许可证 ──
    lic = os.path.join(PKG, "licenses", "COPYING")
    check(os.path.isfile(lic), "licenses/COPYING 随包分发")
    if os.path.isfile(lic):
        with open(lic, "rb") as fh:
            txt = fh.read(4096).decode("utf-8", "replace")
        check("GNU GENERAL PUBLIC LICENSE" in txt.upper(),
              "COPYING 为 GNU GPL 正文（模块 license=GPL-2.0-or-later）")


def layer2_consumer_e2e():
    """编译并真实运行消费者 E2E 宿主，返回 (passed, failed, skipped)。"""
    print("\n== 层 2：消费者 E2E（dlopen + 最小核心桩，真实执行）==\n")

    if not E2E_SRC or not os.path.isfile(E2E_SRC):
        print("[skip] 未提供 SLACK_E2E_SRC（e2e_consumer.c），层 2 跳过")
        return 0, 0, 1

    out_dir = BUILD_DIR or tempfile.mkdtemp(prefix="slack-e2e-")
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        print("[FAIL] E2E 输出目录不可创建：%s（%s）" % (out_dir, exc))
        return 0, 1, 0

    cc = CC if os.path.isabs(CC) else (shutil.which(CC) or CC)
    binary = os.path.join(out_dir, "e2e_consumer")
    cmd = [cc, "-O1", "-Wall", "-rdynamic", E2E_SRC, "-o", binary]
    print("       编译: %s" % " ".join(cmd))
    try:
        built = subprocess.run(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=600)
    except Exception as exc:
        print("[FAIL] E2E 宿主编译异常：%s" % exc)
        return 0, 1, 0
    if built.returncode != 0:
        print(built.stdout.decode("utf-8", "replace"))
        print("[FAIL] E2E 宿主编译失败（RC=%d）" % built.returncode)
        return 0, 1, 0

    run_env = dict(os.environ)
    if DEP_LIBDIRS:
        prev = run_env.get("LD_LIBRARY_PATH", "")
        run_env["LD_LIBRARY_PATH"] = DEP_LIBDIRS + ((":" + prev) if prev else "")
    print("       运行: %s %s" % (binary, MODULE))
    print("       LD_LIBRARY_PATH=%s" % run_env.get("LD_LIBRARY_PATH", ""))
    print("")
    try:
        proc = subprocess.run([binary, MODULE], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, env=run_env, timeout=600)
    except Exception as exc:
        print("[FAIL] E2E 运行异常：%s" % exc)
        return 0, 1, 0

    text = proc.stdout.decode("utf-8", "replace")
    print(text.rstrip())

    passed = failed = 0
    for line in text.splitlines():
        if "== 结果：" in line:
            fields = line.strip().strip("=").strip()
            # 形如 "结果：32 passed, 0 failed"
            for token in fields.replace("：", " ").split():
                if token.isdigit():
                    if "passed" in fields and passed == 0:
                        passed = int(token)
                    elif "failed" in fields:
                        failed = int(token)
    if proc.returncode != 0 and failed == 0:
        failed = 1
    print("\n       层 2 结果：%d passed, %d failed" % (passed, failed))
    return passed, failed, 0


def main():
    layer1_structure()
    e2e_pass, e2e_fail, e2e_skip = layer2_consumer_e2e()

    print("\n== 结果 ==")
    print("层 1 产物结构：%d passed, %d failed, %d skipped"
          % (L1_PASS, L1_FAIL, L1_SKIP))
    print("层 2 消费者 E2E：%d passed, %d failed, %d skipped"
          % (e2e_pass, e2e_fail, e2e_skip))
    total_pass = L1_PASS + e2e_pass
    total_fail = L1_FAIL + e2e_fail
    print("合计：%d passed, %d failed" % (total_pass, total_fail))
    print("== %s ==" % ("ALL CHECKS PASSED" if total_fail == 0 else "CHECKS FAILED"))
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
