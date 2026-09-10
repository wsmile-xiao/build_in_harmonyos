#!/usr/bin/env python3
"""Conan test_package for mpfrcx 0.6.3 (consumer + OHOS-specific tests)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MpfrcxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # The mpfrcx package only ships its own header; gmp/mpfr/mpc headers
        # live in the dependency packages, so hand their include dirs to the
        # test the same way the mpc test_package does.
        include_dirs = []
        for dep_name in ("gmp", "mpfr", "mpc"):
            include_dir = os.path.join(
                self.dependencies[dep_name].package_folder, "include"
            )
            if os.path.isdir(include_dir):
                include_dirs.append(include_dir)

        tc = CMakeToolchain(self)
        tc.variables["MPFRCX_TEST_DEP_INCLUDE_DIRS"] = ";".join(include_dirs)
        tc.variables["MPFRCX_LIB_DIR"] = os.path.join(
            self.dependencies["mpfrcx"].package_folder, "lib"
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        for name in ("test_mpfrcx", "ohos_special_test"):
            bin_path = os.path.join(self.cpp.build.bindir, name)
            self.run(bin_path, env="conanrun")
