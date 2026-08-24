#!/usr/bin/env python3
"""Conan test_package for bash-git-prompt — source gitprompt.sh 真实加载验证。

用法: python3 test_bash_git_prompt.py <package_folder>

aireview（#6317 Medium）修复：原实现 PASS 行无条件执行 + 无 set -e——
包内容损坏/函数未定义也必然 PASS（伪通过，违反 R34/R9）。现改为：
bash 侧 set -e + 条件 PASS（任一检查失败立即非零退出），Python 侧三个
标记全部出现才判定通过。
"""
import os
import shutil
import subprocess
import sys

PASS_MARKERS = [
    "PASS: git_prompt_dir 函数已定义",
    "PASS: git_prompt_list_themes 函数已定义",
    "PASS: gitprompt.sh 真实加载成功",
]


def main():
    pkg_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    prompt_dir = os.path.join(pkg_dir, "share", "bash-git-prompt")
    bash = shutil.which("bash") or "/data/service/hnp/bin/bash"
    if not os.path.isfile(bash):
        print("FAIL: bash 解释器不存在（%s）" % bash)
        return 1
    # set -e + 条件 PASS：gitprompt.sh 缺失/source 失败/函数未定义任一
    # 情况都立即以非零码退出——不允许伪通过
    script = (
        "set -e; "
        "export __GIT_PROMPT_DIR='%s'; "
        "test -f '%s/gitprompt.sh' || { echo 'FAIL: gitprompt.sh 不存在'; exit 1; }; "
        "source '%s/gitprompt.sh' || { echo 'FAIL: gitprompt.sh 加载失败'; exit 1; }; "
        "declare -F git_prompt_dir >/dev/null || { echo 'FAIL: git_prompt_dir 未定义'; exit 1; }; "
        "echo 'PASS: git_prompt_dir 函数已定义'; "
        "declare -F git_prompt_list_themes >/dev/null || { echo 'FAIL: git_prompt_list_themes 未定义'; exit 1; }; "
        "echo 'PASS: git_prompt_list_themes 函数已定义'; "
        "echo 'PASS: gitprompt.sh 真实加载成功'" % (prompt_dir, prompt_dir, prompt_dir)
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
        print("FAIL: bash-git-prompt 消费测试未通过（rc=%d，缺失标记=%s）"
              % (r.returncode, missing))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
