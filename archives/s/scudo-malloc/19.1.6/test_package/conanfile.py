#!/usr/bin/env python3
"""Test package for scudo-malloc 19.1.6.

Uses dlopen to load the shared library at runtime, avoiding the static
linking issue where scudo's malloc overrides the system malloc and crashes
during C runtime initialization on OHOS.
"""
import os
import glob

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ScudoMallocTestConan(ConanFile):
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
        # Find the shared library path in the package
        lib_dir = None
        for dep in self.dependencies.values():
            if hasattr(dep, "cpp_info") and hasattr(dep.cpp_info, "libdir"):
                lib_dir = dep.cpp_info.libdir
                break
        if not lib_dir:
            dep = self.dependencies["scudo-malloc"]
            lib_dir = os.path.join(dep.package_folder, "lib") if hasattr(dep, "package_folder") else None
        if not lib_dir or not os.path.isdir(lib_dir):
            self.output.warning("No lib directory found, skipping runtime test")
            return

        so_files = glob.glob(os.path.join(lib_dir, "*.so"))
        if not so_files:
            self.output.warning("No shared library found, skipping runtime test")
            return

        so_file = so_files[0]
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_scudo_malloc")
        self.run(f"{test_bin} {so_file}", env="conanrun")
