#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/berkeley-db5/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Berkeleydb5TestConan(ConanFile):
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
        # Directly run the consumer test program built by CMake (see CMakeLists.txt).
        # test.c genuinely exercises the berkeley-db5 API: db_create() + db->close().
        # The test binary links against the installed libdb-5.3.so, but the conanrun
        # env does NOT automatically include dependency libdirs on OHOS/HMDFS, so
        # LD_LIBRARY_PATH must be injected explicitly (same pattern as other archives).
        # Exits non-zero on any API failure, which fails the conan create test step.
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_berkeley-db5")
        dep = self.dependencies["berkeley-db5"]
        lib_dir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        self.run(
            f'export LD_LIBRARY_PATH="{lib_dir}:$LD_LIBRARY_PATH"; "{bin_path}"',
            env="conanrun",
        )
