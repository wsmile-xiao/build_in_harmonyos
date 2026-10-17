#!/usr/bin/env python3
"""Smoke-test the installed tkn command (offline consumer checks).

上游 tektoncd/cli 的 Go 单元测试（go test ./...）需要 Go 工具链与
Kubernetes/Tekton 测试环境，OHOS 目标侧无法运行；官方二进制发布包也
不携带测试源码。因此本文件自行补充可离线执行的可执行断言，逐条验证
打包后的 tkn 产物。
"""

import pathlib
import subprocess
import sys

PASSED = 0


def check(name, condition, detail=""):
    global PASSED
    if not condition:
        raise RuntimeError(f"[fail] {name}: {detail}")
    PASSED += 1
    print(f"[ok] {name}")


def run(command):
    return subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    ).stdout


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: test_tkn.py <path-to-tkn>")

    exe = pathlib.Path(sys.argv[1])

    # 1. 产物存在性
    check("executable exists", exe.is_file(), f"tkn executable is missing: {exe}")

    # 2. 主帮助识别命令
    help_output = run([str(exe), "--help"])
    check(
        "main help identifies tkn",
        "tekton" in help_output.lower() or "tkn" in help_output.lower(),
    )

    # 3. 主帮助列出核心子命令
    for sub in ("pipeline", "task", "pipelinerun", "taskrun", "completion", "version"):
        check(
            f"main help lists '{sub}' subcommand",
            f"\n  {sub}" in help_output or f"  {sub} " in help_output,
        )

    # 4. version 输出版本信息
    version_output = run([str(exe), "version"])
    check(
        "version output mentions version",
        "version" in version_output.lower(),
        f"Unexpected tkn version output: {version_output!r}",
    )

    # 5. version 输出版本号 0.45.0
    check(
        "version output contains 0.45.0",
        "0.45.0" in version_output,
        f"Missing version 0.45.0 in: {version_output!r}",
    )

    # 6. 子命令帮助可离线执行
    sub_help = run([str(exe), "pipeline", "--help"])
    check(
        "pipeline --help executable",
        "manage pipelines" in sub_help.lower(),
        f"Unexpected pipeline help: {sub_help[:200]!r}",
    )

    # 7. completion 脚本可离线生成
    completion_output = run([str(exe), "completion", "bash"])
    check(
        "completion bash generated",
        "bash completion for tkn" in completion_output,
        f"Unexpected completion output: {completion_output[:200]!r}",
    )

    print(f"tektoncd-cli package checks passed: {PASSED}/{PASSED}")


if __name__ == "__main__":
    main()
