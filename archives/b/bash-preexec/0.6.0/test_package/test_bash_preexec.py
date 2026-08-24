#!/usr/bin/env python3
"""Conan test_package for bash-preexec — source bash-preexec.sh 真实加载验证。

用法: python3 test_bash_preexec.py <package_folder>

aireview（#6319 Medium）修复：原实现 PASS 行无条件执行 + 无 set -e——
包内容损坏/脚本语法错误/函数未定义也必然 PASS（伪通过，违反 R34/R9）。
现改为：bash 侧 set -e + 条件 PASS（任一检查失败立即非零退出），Python
侧三个标记全部出现 + rc=0 才判定通过。
"""
import os
import shutil
import subprocess
import sys

PASS_MARKERS = [
    "PASS: __bp_install 函数已定义",
    "PASS: __bp_precmd_invoke_cmd 函数已定义",
    "PASS: bash-preexec.sh 真实加载成功",
]


def main():
    pkg_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    share = os.path.join(pkg_dir, "share", "bash-preexec")
    bash = shutil.which("bash") or "/data/service/hnp/bin/bash"
    if not os.path.isfile(bash):
        print("FAIL: bash 解释器不存在（%s）" % bash)
        return 1
    # set -e + 条件 PASS：bash-preexec.sh 缺失/source 失败/任一函数未定义
    # 都立即以非零码退出——不允许伪通过
    script = (
        "set -e; "
        "test -f '%s/bash-preexec.sh' || { echo 'FAIL: bash-preexec.sh 不存在'; exit 1; }; "
        "source '%s/bash-preexec.sh' || { echo 'FAIL: bash-preexec.sh 加载失败'; exit 1; }; "
        "declare -F __bp_install >/dev/null || { echo 'FAIL: __bp_install 未定义'; exit 1; }; "
        "echo 'PASS: __bp_install 函数已定义'; "
        "declare -F __bp_precmd_invoke_cmd >/dev/null || { echo 'FAIL: __bp_precmd_invoke_cmd 未定义'; exit 1; }; "
        "echo 'PASS: __bp_precmd_invoke_cmd 函数已定义'; "
        "echo 'PASS: bash-preexec.sh 真实加载成功'" % (share, share)
    )
    r = subprocess.run([bash, "-c", script], capture_output=True, text=True,
                       timeout=120,
                       env=dict(os.environ, PATH="/data/service/hnp/bin:/system/bin:" +
                                os.environ.get("PATH", "")))
    out = (r.stdout or "") + (r.stderr or "")
    print(out)
    # 三个标记必须全部出现，且 bash 退出码为 0
    missing = [m for m in PASS_MARKERS if m not in out]
    if r.returncode != 0 or missing:
        print("FAIL: bash-preexec 消费测试未通过（rc=%d，缺失标记=%s）"
              % (r.returncode, missing))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
