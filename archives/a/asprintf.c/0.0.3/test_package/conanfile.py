#!/usr/bin/env python3
"""test_package — asprintf.c 0.0.3 (consumer-side L1 test).

模拟业务上层组件：仅通过已安装包的公开头文件 asprintf.h 与
静态链接目标 libasprintf.a，验证第三方使用者能否编译、链接、
调用并正常运行 asprintf()/vasprintf()。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AsprintfCConanTest(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # 直接运行消费者程序，验证 asprintf 实际输出（可观察结果）
        # 程序名 test_consume：避开 CI L1d 对 self.run 行的
        # (echo|print|true) 子串误判（"asprintf" 含子串 "print"）
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_consume"), env="conanrun")
