#!/usr/bin/env python3
"""Conan test_package — tdb 1.4.15 consumer test (Conan L1)"""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class TdbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

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
            return
        tdb_dep = self.dependencies[self.tested_reference_str]
        libdir = os.path.join(tdb_dep.package_folder, "lib")
        bindir = os.path.join(tdb_dep.package_folder, "bin")
        exe = os.path.join(self.cpp.build.bindir, "test_tdb")
        self.run(
            f'export LD_LIBRARY_PATH="{libdir}:{bindir}:$LD_LIBRARY_PATH"; "{exe}"',
            env="conanrun",
        )
        self.run(
            f'export LD_LIBRARY_PATH="{libdir}:{bindir}:$LD_LIBRARY_PATH"; '
            f'"{bindir}/tdbdump" test_tdb.tdb',
            env="conanrun",
        )
