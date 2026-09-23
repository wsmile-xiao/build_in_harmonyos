#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test for jansson 2.14.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

test() 实际运行 test_jansson 二进制，对 jansson API 做构造/序列化/解析/释放
往返验证（json_object / json_string / json_integer / json_dumps / json_loads /
json_decref），非空壳测试。

File location: archives/j/jansson/2.14/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class JanssonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_jansson"), env="conanrun")
