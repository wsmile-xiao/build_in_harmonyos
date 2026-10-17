#!/usr/bin/env python3
"""Conan test_package for GEOS 3.13.0."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class GeosTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verify compile and link")
            return
        bash = os.environ.get("CONFIG_SHELL", "")
        if not bash or not os.path.exists(bash):
            bash = ""
            for candidate in ["/data/service/hnp/bin/bash", "/usr/bin/bash", "/bin/bash"]:
                if os.path.exists(candidate):
                    bash = candidate
                    break
        if bash:
            self.run(f"{bash} -c './test_geos'", env="conanrun")
        else:
            self.run("./test_geos", env="conanrun")
