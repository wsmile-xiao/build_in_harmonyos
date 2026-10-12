#!/usr/bin/env python3
"""qlog 0.51.1 — test_package smoke driver（由 test_package/conanfile.py 的
test() 通过 self.run 实际执行，L0c/R34 测试源）。

验证内容：
  1. `qlog --version` 启动 QApplication（offscreen QPA，验证整个 Qt6 链接
     闭包）并打印包版本号；
  2. `qlog --help` 校验上游命令行选项齐全（--version/--namespace/
     --language/--debug）。

退出码：0 = 全部断言通过；非 0 = 断言失败（conan test 判负）。
"""
import subprocess
import sys

APP = sys.argv[1]
PKG_VERSION = sys.argv[2]


def run_qlog(*args):
    return subprocess.run(
        [APP, *args], capture_output=True, text=True, timeout=180
    )


def main():
    # 1) --version：QApplication 构造 + QCommandLineParser 打印版本
    result = run_qlog("--version")
    out = result.stdout + result.stderr
    if result.returncode != 0:
        print(f"[FAIL] qlog --version exit={result.returncode}\n{out}")
        return 1
    if PKG_VERSION not in out:
        print(f"[FAIL] --version did not report {PKG_VERSION}: {out!r}")
        return 1
    print(f"[ok] qlog --version reports {PKG_VERSION}")

    # 2) --help：上游命令行选项齐全
    result = run_qlog("--help")
    out = result.stdout + result.stderr
    if result.returncode != 0:
        print(f"[FAIL] qlog --help exit={result.returncode}\n{out}")
        return 1
    for option in ("--version", "--namespace", "--language", "--debug"):
        if option not in out:
            print(f"[FAIL] --help missing upstream option {option}")
            return 1
    print("[ok] qlog --help advertises all upstream options")
    return 0


if __name__ == "__main__":
    sys.exit(main())
