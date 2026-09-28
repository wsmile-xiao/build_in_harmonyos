#!/usr/bin/env python3
"""Consumer test for openkim-models/2021-08-11."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OpenkimModelsTestConan(ConanFile):
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
        dep = self.dependencies["openkim-models"]
        if not os.path.isdir(dep.package_folder):
            raise Exception(
                f"openkim-models package folder not found: "
                f"{dep.package_folder}")
        if not can_run(self):
            self.output.info("Cross-built openkim_models_probe; runtime "
                             "verification is deferred to the OHOS target")
            return
        probe = os.path.join(self.cpp.build.bindir, "openkim_models_probe")
        resource = os.path.join(dep.package_folder, "share", "openkim-models")
        self.run(f'"{probe}" "{resource}"', env="conanrun")
