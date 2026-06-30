#!/usr/bin/env python3
"""Conan test_package — airspyone-host 1.0.10

L1 test: verify the packaged library can be found, linked, and executed.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AirspyonehostTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        # Get the dependency's package lib directory for runtime linking
        dep = self.dependencies["airspyone-host"]
        dep_libdir = os.path.join(dep.package_folder, "lib")
        sys_libdir = os.path.expanduser("~/usr/local/lib")
        ld_path = f"{dep_libdir}:{sys_libdir}"
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_airspyone_host")
        self.run(f'export LD_LIBRARY_PATH="{ld_path}:$LD_LIBRARY_PATH"; {bin_path}', env="conanrun")
