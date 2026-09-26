#!/usr/bin/env python3
"""Conan test_package for uncrustify 0.79.0 — 真实驱动已安装的 uncrustify.

用例全部写在 test.sh 里真实执行（PF3/R34：非空壳、非 print-only）：
版本冒烟、help 冒烟、配置驱动的 C 格式化与黄金输出逐字节比对、
格式化幂等性、stdin 通道与文件通道等价、错误路径退出码，以及两条
鸿蒙平台专项断言（已安装 ELF 为 AArch64 且自带 .codesign 执行段、
经 hnp bash 包装在 OHOS 沙箱内真实执行）。

test_package 是消费方视角，不计入上游测试分母（PR 模板「鸿蒙特有测试」行）。
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class UncrustifyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test.sh", "sample.c", "style.cfg", "expected.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        bindir = os.path.join(
            self.dependencies["uncrustify"].package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run('sh "%s" "%s" "%s" "%s"' % (
            script, bindir, self.recipe_folder, self.build_folder),
            env="conanrun")
