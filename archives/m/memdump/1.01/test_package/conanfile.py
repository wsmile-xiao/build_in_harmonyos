#!/usr/bin/env python3
"""Conan test_package — memdump 1.01 消费者测试（真实执行交付的二进制并断言行为）。"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MemdumpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        name = self.tested_reference_str.split("/")[0]
        pkg_folder = self.dependencies[name].package_folder
        memdump = os.path.join(pkg_folder, "bin", "memdump")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_memdump")
        # 传制品绝对路径：既真实执行被测包，也让 CI 的 L1e 破坏性反向验证
        # （把产物目录移走）必然失败，而不是空跑
        self.run(f'"{test_bin}" "{memdump}"', env="conanrun")
