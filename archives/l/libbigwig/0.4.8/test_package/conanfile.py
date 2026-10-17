#!/usr/bin/env python3
"""Conan test_package — libbigwig 0.4.8 consumer round-trip test.

Builds test_roundtrip.c against the packaged library and runs it. The test
writes a bigWig file, reopens it and verifies every entry, so a failure here
means the packaged library cannot perform its core function.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibbigwigTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # bigWigIO.h 直接 #include <curl/curl.h>;按 cpr 1.12.0 同款先例,把 curl
        # 声明为 test_package 的直接依赖,确保 CMakeDeps 为消费者生成完整的
        # CURL 配置(tested_reference 方式解析时,传递依赖 curl 的 cpp_info
        # 生成的 include 目录可能为空)
        self.requires("curl/8.15.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_libbigwig")
        self.run(f'"{binary}"', env="conanrun")
