#!/usr/bin/env python3
"""Conan test_package — tcl-tls 1.7.22 genuine dependency test (R34).

Verifies the tcl-tls shared library can be dlopen'd and the Tls_Init
symbol is present.  If the package's lib/ directory is removed (L1e
destructive test), this test will FAIL — proving genuine dependency.
"""
import os
import glob

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TcltlsTestConan(ConanFile):
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
        # Locate the tcl-tls shared library in the installed package
        dep = self.dependencies["tcl-tls"]
        pkg_folder = str(dep.package_folder)
        so_files = glob.glob(
            os.path.join(pkg_folder, "lib", "tcltls1.7.22", "*.so*")
        )
        assert so_files, (
            f"tcl-tls .so not found in {pkg_folder}/lib/tcltls1.7.22/"
        )
        lib_path = so_files[0]

        # Run the test binary with the library path — genuine dependency test
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_tcl_tls")
        self.run(f'"{test_bin}" "{lib_path}"', env="conanrun")
