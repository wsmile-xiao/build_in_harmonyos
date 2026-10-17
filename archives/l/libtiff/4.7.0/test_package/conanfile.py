#!/usr/bin/env python3
"""Conan test_package — libtiff 4.7.0 L1 functional test.

Write + read back a TIFF image per codec (NONE/PACKBITS/DEFLATE/LZMA/ZSTD/LERC/WEBP),
verifying the real library API and the codec backends provided by conan deps.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building
from conan.tools.env import Environment


class LibtiffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # lerc 等 C++ 依赖的 .so DT_NEEDED libc++_shared.so，由平台 SDK 提供
        # （/system/lib64）。开发机 shell 的 LD_LIBRARY_PATH 常有损坏段
        # （前导空格），conanrun 不含系统目录 → 显式前置，保证加载器可解析。
        run_env = Environment()
        run_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        run_env.vars(self).save_script("system_run_env")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only checking compile+link")
            return
        self.run("ctest --output-on-failure", env=["conanrun", "system_run_env"])
