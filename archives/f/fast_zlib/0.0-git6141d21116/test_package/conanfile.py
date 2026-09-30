#!/usr/bin/env python3
"""Conan test_package for fast_zlib — 消费者视角真实 API 验证 (R34).

通过公开 zlib.h API (compress2/uncompress) 实质调用被测包，
验证编译、链接、运行与数据往返一致性，同时 L0d 门禁要求显式 self.run。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FastzlibTestConan(ConanFile):
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
        # L0d: explicit self.run() required by CI gate
        self.run(os.path.join(self.cpp.build.bindir, "test_fast_zlib"),
                 env="conanrun")