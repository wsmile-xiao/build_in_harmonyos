#!/usr/bin/env python3
"""Consumer test — polylib 6.01.

L1 checks:
  * the packaged C API builds and computes the unit square's polyhedron
    (constraints -> dual, round trip back to constraints);
  * the installed c2p CLI reproduces the same polyhedron.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PolylibTestConan(ConanFile):
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
        if not can_run(self):
            return

        cmake = CMake(self)
        cmake.test()

        tested = self.dependencies[self.tested_reference_str]
        c2p = os.path.join(tested.package_folder, "bin", "c2p")
        square = os.path.join(self.source_folder, "square.in")
        script = os.path.join(self.source_folder, "test_c2p.sh")
        shell = "/system/bin/sh" if str(self.settings.os) == "OHOS" else "sh"
        self.run(f'{shell} "{script}" "{c2p}" "{square}"', env="conanrun")
