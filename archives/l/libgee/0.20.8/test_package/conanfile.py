#!/usr/bin/env python3
"""Conan test_package for libgee 0.20.8 — C API 实质调用验证。

R34: test_package 必须实质调用被测包 API。CMake 方式（同 glib 先例）：
CMakeDeps 通过 cpp_info.requires + transitive_headers/libs 传递 glib 依赖，
test.c 包含 <gee.h>/<glib.h>，创建 GeeArrayList、add 元素、校验集合大小。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibgeeTestConan(ConanFile):
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
        # 直接运行测试二进制（conanrun 环境注入 LD_LIBRARY_PATH）
        self.run("./test_package", env="conanrun")
