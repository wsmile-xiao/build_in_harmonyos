#!/usr/bin/env python3
"""Consumer test for lebiniou-data/3.67.0."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LebiniouDataTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dep = self.dependencies["lebiniou-data"]
        if not os.path.isdir(dep.package_folder):
            raise Exception(
                f"lebiniou-data package folder not found: {dep.package_folder}")
        if not can_run(self):
            self.output.info("Cross-built lebiniou_data_probe; runtime "
                             "verification is deferred to the OHOS target")
            return
        probe = os.path.join(self.cpp.build.bindir, "lebiniou_data_probe")
        self.run(f'"{probe}" "{dep.package_folder}"', env="conanrun")
