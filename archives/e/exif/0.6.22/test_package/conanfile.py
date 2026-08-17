#!/usr/bin/env python3
"""Conan test_package for exif 0.6.22 — CLI tool smoke test (R34).

Verifies the installed `exif` binary is functional via CMake-built
test_exif (which runs exif --version and a missing-file case).
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class ExifTestConan(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    test_type = "explicit"
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
        if cross_building(self):
            self.output.info("cross-building: 编译验证通过，跳过运行时测试")
            return
        # Verify the exif binary exists in the package
        bin_path = os.path.join(self.dependencies["exif"].package_folder,
                                "bin", "exif")
        if not os.path.exists(bin_path):
            raise Exception(f"exif binary not found: {bin_path}")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_exif")
        self.run(f'"{test_bin}"', env="conanrun")
