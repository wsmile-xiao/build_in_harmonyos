#!/usr/bin/env python3
"""test_package for lrcalc 1.2 -- exercises the packaged library and tools.

test.c links liblrcalc through the Conan-generated CMake config and checks
three documented Littlewood-Richardson coefficients; test_lrcalc.sh runs
the packaged `lrcalc` and `schubmult` executables and compares their output
with upstream README examples.  Both legs fail if the package artifact
directories are missing (CI L1e sabotages bin/lib/include).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LrcalcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

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
        # cmake_layout moves the build folder under build/<config>, so run the
        # CLI checks from the test_package source folder explicitly.  /bin/sh
        # is used instead of CONFIG_SHELL because the harmonybrew bash injected
        # by the profile is unreliable on HMDFS (E386 family).
        self.run("/bin/sh test_lrcalc.sh", env="conanrun", cwd=self.source_folder)
