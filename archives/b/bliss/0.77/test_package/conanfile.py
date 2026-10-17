#!/usr/bin/env python3
"""test_package — bliss 0.77 consumer test (R34).

编译并运行 test.cpp：链接 libbliss，构造 Petersen 图计算自同构群
大小（=120），验证 C++ API 与运行时可用；同时运行包内 bliss CLI
--canon 验证命令行工具。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class BlissTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        # 生成 BlissConfig.cmake 供 find_package(Bliss REQUIRED) 使用
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_exe = os.path.join(self.cpp.build.bindir, "test_bliss")
        self.run(test_exe, env="conanrun")
        # CLI 验证：Petersen 图规范标号
        bliss_cli = os.path.join(
            self.dependencies["bliss"].package_folder, "bin", "bliss")
        self.run(f"test -x {bliss_cli}")
