#!/usr/bin/env python3
"""Conan test_package — collections-c 2.3.3 consumer smoke test."""

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
import os


class CollectionsCTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_collections_c")
            self.run(bin_path, env="conanrun")
            # 鸿蒙专项适配测试：池 16 字节对齐 + 2 万次容器压力（R40 深度适配验证）
            ohos_bin = os.path.join(self.cpp.build.bindir, "test_collections_c_ohos")
            self.run(ohos_bin, env="conanrun")
