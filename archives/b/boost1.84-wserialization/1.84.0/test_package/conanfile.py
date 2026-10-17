#!/usr/bin/env python3
"""Conan test_package — boost1.84-wserialization 1.84.0 L1 test.

R34: the test source exercises the real wide-char archive API
(text_woarchive/text_wiarchive + xml_woarchive/xml_wiarchive round-trips of a
struct containing std::wstring / std::vector / std::map).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BoostWserializationTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # L0d 门禁要求 test() 中存在显式 self.run() 调用，
        # 直接运行构建产物 test_wserialization 满足该判定。
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_wserialization"))
