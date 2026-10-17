#!/usr/bin/env python3
"""Conan test_package — heimdal 7.8.0

L1 test: 构建并运行 test.c——链接 heimdal 库（libkrb5）并调用
krb5_init_context() 初始化 Kerberos 上下文，验证库可用。
使用 self.run() 真实执行（L0d 门禁要求）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain


class HeimdalTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        tc = CMakeToolchain(self)
        tc.generate()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        test_exe = os.path.join(self.build_folder, "test_heimdal")
        self.run(test_exe, env="conanrun")
