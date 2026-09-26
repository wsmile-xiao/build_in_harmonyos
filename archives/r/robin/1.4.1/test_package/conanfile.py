#!/usr/bin/env python3
"""Consumer package that builds and runs the upstream Boost.Test suite."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class RobinTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Boost.Test is a test-only dependency; it is not exposed by the
        # header-only robin package itself.
        self.requires("boost/1.84.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        include_dir = self.dependencies["robin"].cpp_info.includedirs[0]
        tc = CMakeToolchain(self)
        tc.variables["ROBIN_INCLUDE_DIR"] = include_dir
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = os.path.join(self.build_folder, "robin_upstream_tests")
        runner = os.path.join(self.source_folder, "run_upstream_tests.py")
        python = os.environ.get("PYTHON", "python3")
        self.run('"%s" "%s" "%s"' % (python, runner, binary), env="conanrun")
