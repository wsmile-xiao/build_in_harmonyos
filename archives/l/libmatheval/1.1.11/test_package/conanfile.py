#!/usr/bin/env python3
"""test_package — libmatheval 1.1.11.

上游 `make check` 的驱动 tests/matheval.c 是 guile 扩展（无条件 #include
<libguile.h>，且用 guile 1.8/2.0 时代已移除的 API），在本仓已适配的 guile 2.2 上
无法编译运行。作为替代，本 test_package 用 libmatheval 的纯 C 公开 API 逐条复现
upstream tests/*.at 的数值 oracle（同一表达式、同一期望值），构建后真机实跑。
"""
import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libmatheval"].cpp_info
        inc = " ".join("-I" + p for p in dep.includedirs)
        libs = " ".join("-L" + p for p in dep.libdirs)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test_matheval.c -o test_matheval {inc} {libs} -lmatheval -lm")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_matheval'", env="conanrun")
