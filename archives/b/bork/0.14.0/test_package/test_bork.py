#!/usr/bin/env python3
"""bork test_package 校验：断言 bin/bork 存在 + bash 语法可解析 + lib 模块已打包。

用 Python 而非 shell（OHOS /system/bin/sh 对脚本语法兼容性差；且工作目录名
含括号 "(1)"，未加引号的路径会报 syntax error: unexpected '('）。
"""
import glob
import os
import shutil
import subprocess
import sys


def _find_bash():
    """定位 bash：优先 OHOS 自带路径，其次 PATH。

    bork 是 bash 脚本，语法校验与实际执行都必须用 bash——用 /system/bin/sh
    校验 bash 语法会误通过/误失败（AI 检视 P3）。
    """
    for cand in ("/data/service/hnp/bin/bash", "/bin/bash",
                 "/usr/bin/bash", "/data/app/bin/bash"):
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return shutil.which("bash")


def main():
    if len(sys.argv) < 2:
        print("FAIL: no package dir provided", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    bork = os.path.join(pkg, "bin", "bork")
    if not os.path.isfile(bork):
        print(f"FAIL: bork 主脚本缺失 {bork}", file=sys.stderr)
        return 1

    # bash 是硬前提：bork 自身即 bash 脚本，找不到 bash 时无法做有效校验，
    # 如实失败（不退回 /system/bin/sh 造成假成功，AI 检视 P2/P3）。
    bash = _find_bash()
    if not bash:
        print("FAIL: 未找到 bash——bork 是 bash 脚本，无法进行有效校验",
              file=sys.stderr)
        return 1

    # bash 语法校验：用 bash -n 而非 /system/bin/sh -n（AI 检视 P3——bork 是 bash
    # 脚本，用 POSIX sh 校验 bash 语法会误通过/误失败）
    r = subprocess.run([bash, "-n", bork], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: bork 语法错误: {r.stderr}", file=sys.stderr)
        return 1

    # lib 模块（declarations/helpers/support）已打包到 <pkg>/lib/
    # bork 按 BASH_SOURCE 推导 BORK_SOURCE_DIR=<pkg> 并 source <pkg>/lib/.../，
    # 故模块必须在 lib/（若错装到 share/，此处与真实运行路径会同时暴露）。
    libdir = os.path.join(pkg, "lib")
    subs = ["declarations", "helpers", "support"]
    for s in subs:
        if not os.path.isdir(os.path.join(libdir, s)):
            print(f"FAIL: bork lib/{s} 模块未打包（期望 {libdir}/{s}）",
                  file=sys.stderr)
            return 1
        if not glob.glob(os.path.join(libdir, s, "*.sh")):
            print(f"FAIL: bork lib/{s} 下无 .sh 模块文件", file=sys.stderr)
            return 1

    # R34 实际执行 bork 二进制（review 修复：不再只做静态存在性 + sh -n，
    # 需真实执行验证可运行性）。bork 自行按脚本位置加载 lib/，无需注入
    # 环境变量（其源码不读 BORK_HOME 等覆盖变量）。
    # 注意命令选择：`bork version` 正常退 0 并输出 "bork <ver>"；
    # 而 `bork --help` 走 case 兜底分支打印用法后 exit 1（上游设计如此，
    # 非错误），若用它做断言会误判失败——故用 version 作为冒烟入口。
    r = subprocess.run([bash, bork, "version"], capture_output=True,
                       text=True, timeout=60)
    if r.returncode != 0:
        print(f"FAIL: bork version 执行失败 rc={r.returncode}: {r.stderr}",
              file=sys.stderr)
        return 1
    # 断言真的跑起来了（输出含 "bork"），排除"脚本空转但退 0"
    out = (r.stdout or "").strip()
    if "bork" not in out:
        print(f"FAIL: bork version 输出异常: {out[:200]!r}", file=sys.stderr)
        return 1
    print("OK: bork 主脚本存在 + bash 语法可解析（bash -n）+ lib/{declarations,"
          "helpers,support} 已打包 + bork version 实际执行并输出版本号: %s" % out.splitlines()[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
