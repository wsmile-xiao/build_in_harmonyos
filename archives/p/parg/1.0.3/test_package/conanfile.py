#!/usr/bin/env python3
"""Conan test_package for parg 1.0.3 — Conan L1 consumer test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

test() 直跑消费者二进制的 4 个用例（link/short/long/reorder，与
CMakeLists.txt 的 4 个 CTest 注册条目一一对应），逐行打印
`parg consumer check '<case>': PASS/FAIL`，可与 conan create 日志对账。
不用 cmake.test()：ctest 汇总只显示条目数，且直跑才对得上
「消费者用例断言已安装制品」的口径（device-facts §二.19）。

File location: archives/p/parg/1.0.3/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PargTestConan(ConanFile):
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
        if not can_run(self):
            return
        exe = os.path.join(self.build_folder, "test_parg")
        for case in ("link", "short", "long", "reorder"):
            self.run(f'"{exe}" {case}', env="conanrun")
