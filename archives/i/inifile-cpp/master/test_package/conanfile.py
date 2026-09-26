#!/usr/bin/env python3
"""Consumer package that builds and runs the upstream Catch2 suite."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class InifileCppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.test_requires("catch2/2.13.10-r0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        include_dir = self.dependencies["inifile-cpp"].cpp_info.includedirs[0]
        tc = CMakeToolchain(self)
        tc.variables["INIFILE_INCLUDE_DIR"] = include_dir
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = os.path.join(self.build_folder, "unit_tests")
        runner = os.path.join(self.source_folder, "run_upstream_tests.py")
        python = os.environ.get("PYTHON", "python3")
        self.run('"%s" "%s" "%s"' % (python, runner, binary), env="conanrun")
