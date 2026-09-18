#!/usr/bin/env python3
"""Conan test_package — eastdc 0.0.0-fbcc34e"""

import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class EastdcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # EAStdC public headers unconditionally include EABase/EAAssert/EAThread
        # headers, so the consumer test needs those include dirs at compile time.
        # Declaring them as direct requires here ensures CMakeDeps generates full
        # data (include paths) for them in the test_package graph.
        self.requires("eabase/0699a15")
        self.requires("eaassert/0.0.0-e5e1812")
        self.requires("eathread/0.0.0-f3c6c54")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 实际执行消费者测试与 OHOS 专项测试两个二进制（L0d 要求 test() 内 self.run）
        bin_dir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bin_dir, "test_consumer"), env="conanrun")
        self.run(os.path.join(bin_dir, "test_ohos_special"), env="conanrun")
