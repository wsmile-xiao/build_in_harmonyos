#!/usr/bin/env python3
"""Consumer test for boost1.84-stacktrace_basic (L1 smoke test).

Runs the packaged boost headers + libboost_stacktrace_basic.a static library
through a CMake consumer (find_package boost1.84-stacktrace_basic COMPONENTS
stacktrace_basic), then executes the built binary.

The binary statically links libc++ (-static-libstdc++, set in CMakeLists.txt)
so it runs without LD_LIBRARY_PATH pointing at the SDK libc++_shared.so —
same approach as the boost1.84-contract test_package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BoostStacktraceBasicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # L0d 门禁：test() 需显式 self.run() 执行构建产物
        # （cmake.test() 之外显式运行一次，验证二进制可执行）
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(
            self.cpp.build.bindirs[0], "test_boost1_84_stacktrace_basic" + suffix
        )
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
