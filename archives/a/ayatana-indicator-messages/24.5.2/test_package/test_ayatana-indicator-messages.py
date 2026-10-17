#!/usr/bin/env python3
"""Smoke test — ayatana-indicator-messages 24.5.2 (test_package 探针).

验证两部分（app uid 只读断言，L0d 由 test() 直接 self.run）：
  1. service 冒烟：安装的 service 可执行文件存在且依赖可解析（不因缺共享库/
     符号而无法启动；exit 127 = 加载器错误，其余视为通过）。
  2. 上游测试真实执行证据：读 build() 阶段 test-gactionmuxer 的运行日志
     （gtest-run.log），断言 6 个 TEST 全部 PASSED（上游 tests/test-gactionmuxer.cpp
     的 Sanity/Empty/AddAndRemove/ActionAttributes/Signals/ActivateAction）。
"""
import os
import subprocess
import sys

executable = sys.argv[1]
build_folder = sys.argv[2] if len(sys.argv) > 2 else ""

# --- 1) service 冒烟 ---
if not os.path.isfile(executable):
    print(f"FAIL: service executable not found: {executable}", file=sys.stderr)
    sys.exit(1)

# 依赖注入 conanrun 环境后启动（LD_LIBRARY_PATH 由 conanrun 提供），
# 2 秒超时；加载器缺库/缺符号时 shell 返回 127
result = subprocess.run(
    f"timeout 2 {executable} > /dev/null 2>&1; test $? -ne 127",
    shell=True,
    check=False,
)
assert result.returncode == 0, f"service failed with loading error (exit {result.returncode})"
print("PASS: service executable starts (deps linked)")

# --- 2) 上游 test-gactionmuxer 真实执行证据（build() 阶段运行日志） ---
if build_folder:
    log = os.path.join(build_folder, "gtest-run.log")
    if not os.path.isfile(log):
        print(f"FAIL: gtest-run.log not found: {log}", file=sys.stderr)
        sys.exit(1)
    content = open(log, encoding="utf-8", errors="replace").read()
    # GTest 摘要：6 个 TEST 全部 OK 且 PASSED
    ok_count = content.count("[       OK ]")
    if ok_count != 6:
        print(f"FAIL: expected 6 OK tests in gtest-run.log, got {ok_count}", file=sys.stderr)
        sys.exit(1)
    if "[  PASSED  ] 6 tests." not in content:
        print("FAIL: gtest-run.log missing 'PASSED 6 tests' summary", file=sys.stderr)
        sys.exit(1)
    print(f"PASS: upstream test-gactionmuxer executed for real: {ok_count}/6 tests PASSED")

print("ayatana-indicator-messages test_package: service smoke + upstream gtest run OK")
