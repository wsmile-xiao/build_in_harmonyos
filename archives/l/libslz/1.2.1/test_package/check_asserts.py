#!/usr/bin/env python3
"""libslz 1.2.1 test_package — 断言汇总（读 ASSERT_OK/ASSERT_FAIL 行，打印并把关）。

用法: check_asserts.py <断言日志> [<断言日志> ...]
退出码: 0 = 至少 1 条断言且 0 条失败；1 = 有失败或断言数为 0。
"""
import sys

total = 0
fails = 0

for path in sys.argv[1:]:
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("ASSERT_OK "):
                total += 1
                print(line)
            elif line.startswith("ASSERT_FAIL "):
                fails += 1
                print(line)

print("ASSERT_TOTAL ok=%d fail=%d" % (total, fails))
if fails or total == 0:
    sys.exit(1)
