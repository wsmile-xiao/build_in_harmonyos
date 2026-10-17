#!/usr/bin/env python3
"""Conan test_package — btree.c 0.6.4 消费者验证。

ctest 运行 test.c（btree_new/btree_set/btree_get/btree_ascend 公开 API
往返断言），并直接以运行时产物 test_btree.c 验证第三方使用者可编译、
链接、调用并正常运行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BtreeCTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_btree.c"), env="conanrun")
