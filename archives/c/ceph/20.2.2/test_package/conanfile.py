#!/usr/bin/env python3
"""Consumer test for the packaged Ceph CRUSH core."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class CephTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])

    def test(self):
        if cross_building(self):
            self.output.info("Cross-building: compile and link test passed")
            return
        executable = os.path.join(
            self.cpp.build.bindirs[0], "test_ceph_crush"
        )
        self.run(executable, env="conanrun")
