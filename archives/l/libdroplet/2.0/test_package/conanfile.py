#!/usr/bin/env python3
"""Conan test_package — libdroplet 2.0 L1 official test.

CI runs this automatically via `conan create` (which invokes test_package).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibdropletTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # droplet.h 无条件 include <openssl/ssl.h>/<libxml/...>/<json-c/...>，
        # 消费者需显式 requires 依赖以解析传递头文件
        self.requires("openssl/3.5.8.1")
        self.requires("libxml2/2.15.3")
        self.requires("json-c/0.18")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # E074: HMDFS jobserver fifo EPERM，禁用并行
        cmake.build(cli_args=["-j1"])

    def test(self):
        self.run(
            f"{self.cpp.build.bindirs[0]}/test_libdroplet", env="conanrun")