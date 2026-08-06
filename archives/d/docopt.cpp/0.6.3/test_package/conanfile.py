#!/usr/bin/env python3
"""Consumer test for docopt.cpp."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class DocoptCppTestConan(ConanFile):
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
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindirs[0], "test_docopt")
            if self.settings.os in ("Linux", "OHOS"):
                package_folder = self.dependencies["docopt.cpp"].package_folder
                libdir = os.path.join(package_folder, "lib")
                self.run(f'LD_LIBRARY_PATH="{libdir}" "{executable}"')
            else:
                self.run(f'"{executable}"', env="conanrun")
