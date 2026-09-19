#!/usr/bin/env python3
"""Conan test_package — libprelude 5.2.0 的 L1 消费者测试。

`conan create` 会自动执行本目录：以“下游使用者”的视角，通过 CMakeDeps 生成的
libprelude::libprelude 目标编译并运行 test.c（真实调用 prelude_string_* 与
IDMEF 对象树 API），从而同时验证：头文件布局、导出符号、libprelude.so 与其
gnutls 依赖链在 OHOS 上可加载。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibpreludeTestConan(ConanFile):
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
        # 直接跑二进制而不是 cmake.test()：ctest 会把失败细节吞进日志文件，
        # env="conanrun" 提供 libprelude.so + gnutls/libgcrypt 的 LD_LIBRARY_PATH。
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libprelude"),
                 env="conanrun")
