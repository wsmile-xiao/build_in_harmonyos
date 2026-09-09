#!/usr/bin/env python3
"""Conan test_package for burp 3.3.0 — 消费测试验证 CLI 工具。

纯 python 消费测试（无需 CMake 编译——只跑打包的 bin/burp）：
python3 test_burp.py <package_folder>
generate() 生成 CMakeDeps+CMakeToolchain 照 a52dec test_package（repo
约定），package_folder 取法照 encfs（self.dependencies["burp"].
package_folder）。
"""
from conan import ConanFile
from conan.tools.cmake import CMakeDeps, CMakeToolchain


class BurpTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def test(self):
        pkg_folder = self.dependencies["burp"].package_folder
        self.run('python3 test_burp.py "%s"' % pkg_folder, env="conanrun")
