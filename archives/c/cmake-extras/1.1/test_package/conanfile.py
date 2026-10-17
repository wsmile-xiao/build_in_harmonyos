#!/usr/bin/env python3
"""Conan test_package for cmake-extras 1.1.

跑法与环境：在**被适配的目标机**上用系统 cmake 以 `cmake -P` 脚本模式加载包内的
每个 CMake 模块，断言模块确实交付了它承诺的 macro/function/变量（R34：测试实质
依赖被测包的产物）。刻意不走 CMakeToolchain/编译器探测——被测对象是数据（.cmake
文本），只要 CMake 能从 CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH 找到并解析它们。
env="conanbuild" 是为了拿到 profile [buildenv] 里的 cmake 路径。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["cmake-extras"].package_folder
            script = os.path.join(os.path.dirname(__file__),
                                  "test_cmake_extras.py")
            self.run('%s "%s" "%s"' % (sys.executable, script, pkg),
                     env="conanbuild")
