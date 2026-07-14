#!/usr/bin/env python3
"""Conan test_package — libsigc++ 2.10.8 (Conan L1 官方测试)

用 CMake (CMakeDeps + CMakeToolchain) 消费被测包，编译器由 Conan toolchain
提供，不裸用 shell 环境变量 (R33)。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibsigcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        # 共享库运行期需要 LD_LIBRARY_PATH
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) 不能 exec ELF，用 bash 包一层执行二进制
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        lib_dir = os.path.join(self.dependencies["libsigc"].package_folder, "lib")
        self.run(f"LD_LIBRARY_PATH={lib_dir} {bash} -c './test_libsigc'")
