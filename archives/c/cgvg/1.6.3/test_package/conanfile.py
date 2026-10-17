#!/usr/bin/env python3
"""test_package for cgvg 1.6.3 — 消费测试（R34 实质验证，非空壳）。

cgvg 上游不携带测试套件（Makefile.am 无 TESTS/check_PROGRAMS，make check
无任何可执行测试）。消费测试在真实 OHOS perl 解释器下对打包产物做端到端
功能冒烟（test_cgvg.py）：
  1. cg <pattern>  递归代码搜索（写 ~/.cgvg 日志并输出匹配）
  2. cg -l         回放上一次搜索结果（~/.cglast）
  3. vg <n>        调用 $EDITOR 打开匹配处 file:line（fake editor 验证）
test_cgvg.py 内含断言，任一失败即非零退出 → conan create 失败。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class CgvgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies[self.tested_reference_str].package_folder
        bin_dir = os.path.join(pkg, "bin")
        if not os.path.isdir(bin_dir):
            raise Exception(f"missing package bin dir: {bin_dir}")
        test_script = os.path.join(os.path.dirname(__file__), "test_cgvg.py")
        self.run(f'"{sys.executable}" "{test_script}" "{bin_dir}"', env="conanrun")
