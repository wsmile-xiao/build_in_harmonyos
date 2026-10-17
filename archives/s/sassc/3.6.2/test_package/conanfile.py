#!/usr/bin/env python3
"""Test package for sassc — R34 真实执行 sassc 编译 SCSS 并校验 CSS 输出."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class SasscTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # R34：真实执行 sassc 编译一段 SCSS 并校验输出（非空壳，yarl
            # test_yarl.py 模式——独立测试脚本 + self.run 调用）
            script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "test_sassc.sh")
            self.run('sh "{}"'.format(script), env="conanrun")
