"""selftest — 一键冒烟测试入口（v12.6 L5）。

用法: ohc-run.py selftest
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


def selftest_cli(argv: list[str] | None = None) -> int:
    tests_dir = Path(__file__).resolve().parent.parent.parent / "tests"
    loader = unittest.TestLoader()
    suite = loader.discover(str(tests_dir), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1
