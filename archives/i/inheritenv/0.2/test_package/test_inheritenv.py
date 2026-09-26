#!/usr/bin/env python3
"""Test that inheritenv.el is properly installed, carries its release
markers, and — when emacs is present on the host — that the upstream ERT
suite passes against the packaged file."""
import os
import shutil
import subprocess
import sys


def main():
    pkg_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    lisp_dir = os.path.join(pkg_dir, "lib", "site-lisp")
    el_file = os.path.join(lisp_dir, "inheritenv.el")
    tests_file = os.path.join(lisp_dir, "inheritenv-tests.el")

    failures = []

    # [1] 发行文件在位且非空
    for f in (el_file, tests_file):
        if not os.path.isfile(f):
            failures.append(f"missing {os.path.basename(f)}")
        elif os.path.getsize(f) == 0:
            failures.append(f"empty {os.path.basename(f)}")

    # [2] inheritenv.el 发行标记（文件头 / 版本 / provide / 两个宏 / GPL）
    # 缺失已由 [1] 记录，此处守卫避免 FileNotFoundError 掩盖已收集的失败
    if os.path.isfile(el_file):
        with open(el_file, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    else:
        content = ""
    for marker in (
        ";;; inheritenv.el",
        ";; Version: 0.2",
        "(provide 'inheritenv)",
        "(defmacro inheritenv ",
        "(defmacro inheritenv-add-advice ",
        "GNU General Public License",
    ):
        if marker not in content:
            failures.append(f"missing marker in inheritenv.el: {marker!r}")

    # [3] 测试文件携带上游 ERT 用例（缺失已由 [1] 记录，此处守卫同上）
    if os.path.isfile(tests_file):
        with open(tests_file, encoding="utf-8", errors="replace") as fh:
            tests_content = fh.read()
    else:
        tests_content = ""
    if "(ert-deftest inheritenv-test-propagation" not in tests_content:
        failures.append("missing ERT test inheritenv-test-propagation")

    # [4] 宿主有 emacs 时原样运行上游 ERT 测试命令
    # （等价上游 Makefile test 目标，去掉需 MELPA 联网的 package-lint）
    emacs = shutil.which("emacs")
    ert_ran = False
    if emacs:
        ert_ran = True
        cmd = [emacs, "-Q", "--batch", "-L", lisp_dir,
               "-l", "inheritenv.el", "-l", "inheritenv-tests.el",
               "-f", "ert-run-tests-batch-and-exit"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            tail = "\n".join(result.stdout.splitlines()[-10:])
            failures.append(f"upstream ERT suite failed:\n{tail}")
    else:
        print("NOTE: emacs not found on this host; upstream ERT suite skipped")

    if failures:
        sys.exit("ERROR: " + "; ".join(failures))
    print("PASS: inheritenv.el installed with 0.2 markers"
          + ("; upstream ERT suite passed" if ert_ran else
             " (ERT suite skipped: no emacs)"))
    sys.exit(0)


if __name__ == "__main__":
    main()
