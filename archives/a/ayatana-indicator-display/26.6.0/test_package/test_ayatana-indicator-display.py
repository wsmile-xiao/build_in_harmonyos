#!/usr/bin/env python3
"""Smoke test — ayatana-indicator-display-service.

验证安装的 service 可执行文件存在且依赖可解析（不因缺共享库/符号而
无法启动）。service 为桌面指示器守护进程，无 DBus 会话时启动后
很快退出属预期；只要不是加载器错误（exit 127）即视为通过。
"""
import subprocess
import sys

executable = sys.argv[1]

# 先确认文件存在
import os
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

print("ayatana-indicator-display smoke test: service starts (deps linked)")
