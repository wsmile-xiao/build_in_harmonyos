#!/usr/bin/env python3
"""Conan consumer test for the libdbi SQLite3 driver."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibdbiDriversTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Keep Conan's generated build files and presets outside the source
        # archive so the repository junk-file gate remains clean.
        cmake_layout(self, build_folder="$TMP")

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.user_presets_path = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return

        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libdbi_drivers")
        driver_dir = os.path.join(
            self.dependencies["libdbi-drivers"].package_folder, "lib", "dbd"
        )
        database_dir = os.path.join(self.build_folder, "database")
        os.makedirs(database_dir, exist_ok=True)
        self.run(
            f'"{test_bin}" "{driver_dir}" "{database_dir}"',
            env="conanrun",
        )
