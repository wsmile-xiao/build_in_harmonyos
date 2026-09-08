#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class Libantlr3cTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    requires = "libantlr3c/3.5.3"

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # cmake_layout 单配置生成器: consumer_tests 直接落在 build 目录根部
            # (= self.cpp.build.bindir), 不经 ctest 转发, 只真实执行一次
            executable = os.path.join(self.cpp.build.bindir, "consumer_tests")
            self.run(executable, env="conanrun")
