#!/usr/bin/env python3
"""test_interegular — interegular 0.3.3 test_package consumer test.

验证 interegular 安装后可正常导入并执行基本功能（与 conanfile.py test() 同构，
用于 L0 test_sources 门禁）。
"""
import os
import sys
import unittest

try:
    from interegular import parse_pattern, Comparator, REFlags
except ImportError:
    # 当作为独立脚本运行时，可能需要设置 PYTHONPATH
    pythonpath = os.environ.get("PYTHONPATH", "")
    if pythonpath:
        sys.path.insert(0, pythonpath)
    from interegular import parse_pattern, Comparator, REFlags


class TestInteregular(unittest.TestCase):

    def test_import(self):
        """验证基本导入"""
        from interegular import parse_pattern, Comparator, REFlags
        self.assertTrue(True)

    def test_parse_a_plus(self):
        """解析 a+ 并验证匹配"""
        fsm = parse_pattern("a+").to_fsm()
        self.assertTrue(fsm.accepts("a"))
        self.assertTrue(fsm.accepts("aaaa"))
        self.assertFalse(fsm.accepts(""))
        self.assertFalse(fsm.accepts("b"))

    def test_intersection_detection(self):
        """验证交叉检测"""
        comp = Comparator.from_regexes({"A": "a+", "B": "[ab]+"})
        collisions = list(comp.check())
        self.assertEqual(len(collisions), 1)
        self.assertEqual(collisions[0], ("A", "B"))

    def test_no_intersection(self):
        """验证不交叉的情况"""
        comp = Comparator.from_regexes({"A": "a+", "C": "b+"})
        collisions = list(comp.check())
        self.assertEqual(len(collisions), 0)


if __name__ == "__main__":
    unittest.main()