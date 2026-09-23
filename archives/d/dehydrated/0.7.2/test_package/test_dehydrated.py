#!/usr/bin/env python3
"""dehydrated 0.7.2 consumer test — pure Bash ACME client smoke verification.

Checks the installed package: bin/dehydrated exists, is executable, has a
Bash shebang, passes `bash -n` syntax check, and `--version` really executes
(inside the script this runs its dependency check: grep/mktemp/diff/sed/awk/
curl/cut/head/tail/hexdump/openssl plus sed ERE support) with the expected
version output. Exits non-zero on failure.
"""
import os
import subprocess
import sys


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else "."
    failures = 0

    script = os.path.join(pkg_root, "bin", "dehydrated")
    # 断言 1: 主脚本存在（L1e 破坏性反向验证的失败点）
    if not os.path.isfile(script):
        print("[FAIL] %s missing" % script)
        return 1
    print("[ok] dehydrated script present")

    # 断言 2: 可执行位
    if not os.access(script, os.X_OK):
        print("[FAIL] dehydrated is not executable")
        failures += 1
    else:
        print("[ok] dehydrated is executable")

    # 断言 3: bash 解释器 shebang
    with open(script, "rt", encoding="utf-8", errors="replace") as f:
        shebang = f.readline().strip()
    if "bash" not in shebang:
        print("[FAIL] unexpected shebang: %s" % shebang)
        failures += 1
    else:
        print("[ok] shebang: %s" % shebang)

    # OHOS hnp bash 在部分执行上下文 getcwd() 失败 → 内置 PWD 未定义
    # （脚本 set -u 会因 ${PWD} 未绑定退出）；启动时显式传 PWD 规避。
    # OHOS bash 位于 /data/service/hnp/bin（不在标准 PATH，atool/cvsweb 先例），
    # CI worker 上 os.environ.get("BASH") 未设置，必须用绝对路径兜底。
    bash = os.environ.get("BASH") or "/data/service/hnp/bin/bash"
    script_dir = os.path.dirname(script)
    env = dict(os.environ)
    env["PWD"] = script_dir

    # 断言 4: bash -n 语法自检
    proc = subprocess.run([bash, "-n", script], capture_output=True, text=True,
                          env=env, cwd=script_dir)
    if proc.returncode != 0:
        print("[FAIL] bash -n syntax check failed:\n%s" % proc.stderr.strip())
        failures += 1
    else:
        print("[ok] bash -n syntax OK")

    # 断言 5+6: --version 冒烟（真实触发脚本内置依赖检查）并核对版本输出
    proc = subprocess.run([bash, script, "--version"], capture_output=True, text=True,
                          env=env, cwd=script_dir)
    if proc.returncode != 0:
        print("[FAIL] --version smoke failed (rc=%d):\n%s" % (proc.returncode, proc.stderr.strip()))
        failures += 1
    else:
        print("[ok] --version smoke OK")
        if "Dehydrated version: 0.7.2" not in proc.stdout:
            print("[FAIL] version output mismatch:\n%s" % proc.stdout.strip())
            failures += 1
        else:
            print("[ok] version output: Dehydrated version: 0.7.2")

    if failures:
        print("dehydrated: %d assertion(s) failed" % failures)
        return 1
    print("dehydrated package OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
