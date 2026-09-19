#!/usr/bin/env python3
"""bbhash 1.0.0 消费者测试（Conan L1）。

CI 通过 `conan create` 自动运行 test_package：
- test.cpp：仅经公开头 BooPHF.h 构造 10 万 key 的 minimal perfect hash 并核验全部 lookup 唯一；
- ohos_test.cpp：-Werror 严格编译 + 4 线程 pthread 构造 + save/load 流往返一致。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BbhashTestConan(ConanFile):
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
        # L0d: test() 必须通过 self.run() 实际执行测试二进制（真实运行，非空壳）。
        bindir = os.path.join(self.cpp.build.bindirs[0])
        self.run(os.path.join(bindir, "test_bbhash"), env="conanrun")
        self.run(os.path.join(bindir, "test_bbhash_ohos"), env="conanrun")
