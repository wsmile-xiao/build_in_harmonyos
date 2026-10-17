#!/usr/bin/env python3
"""消费者视角验证：真实执行被测包内的 pforth_standalone（R34）。"""
import subprocess
import sys

executable = sys.argv[1]

# 通过 stdin 传入 Forth 代码，验证 Forth 内核真实求值。
# "3 4 + ." 输出 "7 "，"2 3 * ." 输出 "6 "。
code = "3 4 + .\n2 3 * .\nbye\n"
result = subprocess.run(
    [executable, "-q"],
    input=code,
    capture_output=True,
    text=True,
    timeout=60,
    check=False,
)

output = result.stdout + result.stderr
assert result.returncode == 0, (result.returncode, output)
assert "7" in output, output
assert "6" in output, output

print("pforth CLI smoke test: Forth evaluation (3 4 + . => 7, 2 3 * . => 6) passed")
