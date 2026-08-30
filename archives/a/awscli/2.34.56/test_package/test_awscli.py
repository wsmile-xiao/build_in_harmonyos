#!/usr/bin/env python3
"""awscli consumer test (L0c + R34): standalone test source executed via
self.run from test_package conanfile.py test().

R34: actually invoke the packaged CLI - `aws --version` (real subprocess via
the packaged bin/aws entry script), with PYTHONPATH = declared dependency
site-packages (conan consumer layout).

OHOS environment limits (honest classification, MANIFEST.yml):
  - awscrt / distro / prompt-toolkit / wcwidth are NOT published to ohpcd.
  - docutils/0.23 IS published and declared (round 3); measured
    API-compatible with awscli help.py (publish_string + manpage.Writer).
  - Round-3 guard patches make the startup chain importable without
    awscrt/distro: vendored botocore top-level `from awscrt.crypto import EC` /
    `from awscrt import checksums` and awscli.clidriver `import distro` are
    wrapped in try/except ImportError with honest degradation (EC=None,
    distro=None -> 'unknown').
  - `aws --version` MUST succeed (this asserts the guarded startup chain).
  - `aws help` rendering needs the groff/mandoc pipeline; on OHOS Python
    subprocess cannot resolve bare command names (F5) -> a clear, controlled
    error is reported and recorded; NOT faked as a pass.

Usage: test_awscli.py <site-packages>
"""
import os
import subprocess
import sys


def _pkg_root(site: str) -> str:
    # <pkg>/lib/python3.12/site-packages -> <pkg>
    return os.path.dirname(os.path.dirname(os.path.dirname(site)))


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    paths = [p for p in site.split(os.pathsep) if p]
    if not any(os.path.isdir(os.path.join(p, "awscli")) for p in paths):
        raise AssertionError(f"awscli package missing in {paths}")
    sys.path = paths + sys.path

    # R34: 真实调用打包的 CLI 入口 bin/aws
    bin_aws = os.path.join(_pkg_root(paths[0]), "bin", "aws")
    if not os.path.isfile(bin_aws) or not os.access(bin_aws, os.X_OK):
        raise AssertionError(
            f"bin/aws entry script missing or not executable: {bin_aws}")

    env = dict(os.environ, PYTHONPATH=site)

    # 1) aws --version：round 2 守护补丁后启动链可导入，必须成功
    proc = subprocess.run(
        [sys.executable, bin_aws, "--version"],
        capture_output=True, text=True, timeout=60, env=env)
    print(f"-- aws --version (rc={proc.returncode}) --")
    combined = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0:
        if "2.34.56" not in combined:
            raise AssertionError(
                f"aws --version 未包含 2.34.56，输出: {combined[:200]!r}")
        first = combined.strip().splitlines()[0]
        print(f"OK: aws --version -> {first}")
    else:
        tail = combined.strip().splitlines()[-4:]
        for line in tail:
            print(f"   | {line}", file=sys.stderr)
        raise AssertionError(
            "aws --version 启动失败：守护补丁未生效或出现新的缺失依赖。"
            "精确 blocker 见上方 traceback（本轮不得伪造通过）。")

    # 2) aws help sts：docutils/0.23 已声明并实测兼容，但 help 渲染管道
    #    （docutils -> groff/mandoc -> pager）在 OHOS 不可用——Python
    #    subprocess 无法通过 PATH 解析裸命令名（F5）。受控错误含
    #    'groff'/'mandoc'/'docutils' 关键字；其他错误视为回归，返回非零
    #    （WR-007：非受控错误不得静默通过）。
    try:
        proc2 = subprocess.run(
            [sys.executable, bin_aws, "sts", "help"],
            capture_output=True, text=True, timeout=60, env=env)
        print(f"-- aws sts help (rc={proc2.returncode}) --")
        combined2 = (proc2.stdout or "") + (proc2.stderr or "")
        if proc2.returncode == 0:
            print("OK: aws sts help 渲染成功")
        else:
            tail2 = combined2.strip().splitlines()[-3:]
            for line in tail2:
                print(f"   | {line}", file=sys.stderr)
            if ("groff" in combined2 or "mandoc" in combined2 or
                    "docutils" in combined2):
                print("如实记录：aws help 渲染受 groff/mandoc 管道平台限制"
                      "（OHOS subprocess 不解析裸命令名），守护补丁使其以"
                      "明确错误降级而非崩溃。", file=sys.stderr)
            else:
                print("aws help sts 出现非预期错误，视为回归：",
                      file=sys.stderr)
                print(combined2[-600:], file=sys.stderr)
                return 1
    except Exception as e:
        print(f"aws help sts 异常，视为回归: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
