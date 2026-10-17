#!/usr/bin/env python3
"""Conan test_package for libmysofa 1.3.5.

Builds and runs two consumer executables against the packaged libmysofa:
  - test_libmysofa: open a real SOFA file (data/testfile.sofa), fetch an
    HRTF filter via mysofa_getfilter_float and verify finite outputs
  - ohos_special_test: HarmonyOS-specific checks (coordinate roundtrip,
    filter finite values, minphase/resample, multithreaded lookups)
Both run via ctest inside test(); the L0d gate requires test() to actually
execute the built binaries (R34/PF3 - no empty shells).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class LibmysofaTestConan(ConanFile):
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
        # L0d gate: explicitly run the tested binaries (no empty shell).
        # 数据文件 data/testfile.sofa 由 CMake 在构建期从 base64 解码到
        # <build>/data/，二进制与 ctest 工作目录均在 bin_dir，直接运行
        # 须以 bin_dir 为 cwd（与 ctest WORKING_DIRECTORY 一致）
        bin_dir = os.path.abspath(self.cpp.build.bindirs[0])
        self.run(os.path.join(bin_dir, "test_libmysofa"), env="conanrun",
                 cwd=bin_dir)
        self.run(os.path.join(bin_dir, "ohos_special_test"), env="conanrun",
                 cwd=bin_dir)