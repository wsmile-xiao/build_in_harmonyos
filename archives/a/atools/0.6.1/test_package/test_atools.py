#!/usr/bin/env python3
"""test_package/test_atools.py — atools 消费测试（真实 API——非 stub）"""
import os
import sys

site_pkg = sys.argv[1] if len(sys.argv) > 1 else ""
if site_pkg:
    sys.path.insert(0, site_pkg)

import atools
from atools import memoize

# 真实调用 atools 的 memoize 装饰器（验证打包正确性）
@memoize
def double(x):
    return x * 2

assert double(2) == 4, "memoize 装饰器调用失败"
print("PASS: atools import + memoize OK")
