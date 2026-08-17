#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/e2fsprogs/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class E2FsprogsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # 设备 profile 的 user_toolchain(ohos.toolchain.cmake) 把
        # CMAKE_FIND_ROOT_PATH_MODE_PACKAGE 钉成 ONLY，find_package(CONFIG) 只搜 sysroot，
        # 找不到 CMakeDeps 生成的 e2fsprogs-config.cmake。显式 <Name>_DIR 优先于
        # FIND_ROOT_PATH 搜索，直接命中生成目录（libxslt 案同款修法）。
        cmake.configure(variables={"e2fsprogs_DIR": self.generators_folder})
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_e2fsprogs')}", env="conanrun")
