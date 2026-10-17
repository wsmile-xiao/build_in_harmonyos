#!/usr/bin/env python3
"""Conan test_package — interegular 0.3.3 (Conan L1 test).

验证安装后的 interegular 可以正常导入并执行基本功能。
"""
import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class InteregularTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        python_exe = sys.executable

        # 测试1：基本 import
        test_import = (
            "from interegular import parse_pattern, Comparator, REFlags; "
            "print('import OK')"
        )
        self.run(f'{python_exe} -c "{test_import}"')

        # 测试2：基本功能 - 解析正则并检查匹配
        test_func = (
            "from interegular import parse_pattern; "
            "fsm = parse_pattern('a+').to_fsm(); "
            "assert fsm.accepts('a'), 'a+ should accept a'; "
            "assert fsm.accepts('aaaa'), 'a+ should accept aaaa'; "
            "assert not fsm.accepts(''), 'a+ should not accept empty'; "
            "assert not fsm.accepts('b'), 'a+ should not accept b'; "
            "print('functional test OK')"
        )
        self.run(f'{python_exe} -c "{test_func}"')

        # 测试3：交叉检测
        test_intersect = (
            "from interegular import Comparator; "
            "comp = Comparator.from_regexes({'A': 'a+', 'B': '[ab]+'}); "
            "collisions = list(comp.check()); "
            "assert len(collisions) == 1 and collisions[0] == ('A', 'B'), "
            "'a+ and [ab]+ should intersect'; "
            "print('intersection test OK')"
        )
        self.run(f'{python_exe} -c "{test_intersect}"')