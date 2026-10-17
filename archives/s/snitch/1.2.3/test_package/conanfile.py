#!/usr/bin/env python3
"""Conan test_package for snitch 1.2.3 — Conan L1 consumer test.

这是五级测试体系中的 L1：CI 通过 `conan create` 自动执行（PF3 要求
test() 含真实 self.run 执行逻辑）。

消费视角验证已打包的 snitch 制品：test_snitch.cpp 注册 3 个消费者用例
（基础断言 / 字符串匹配器 / section+capture），由**已安装的 snitch 库**
（with_main=ON 自带 main）驱动执行；全部通过时 snitch 打印
`success: all tests passed (3 tests, N assertions)` 且进程退出码为 0，
可与 conan create 日志逐行对账。

不用 cmake.test()/ctest：ctest 汇总只显示条目数，直跑才对得上
「消费者用例断言已安装制品」的口径（device-facts §二.19，parg 先例）。

File location: archives/s/snitch/1.2.3/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class SnitchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def configure(self):
        # 主配方同款（arrow 先例）：CI profile 默认 cppstd=17，
        # snitch 头（target_compile_features cxx_std_20）强制 C++20。
        self.settings.compiler.cppstd = "20"

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
        exe = os.path.join(self.build_folder, "test_snitch")
        self.run(f'"{exe}"', env="conanrun")
