#!/usr/bin/env python3
"""Consumer test for the dcadec library and packaged CLI."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DcadecTestConan(ConanFile):
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
        cmake.ctest(cli_args=["--output-on-failure"])
        dependency = self.dependencies[self.tested_reference_str]
        cli = os.path.join(dependency.package_folder, "bin", "dcadec")
        self.run('"{}" --help'.format(cli), env="conanrun")
