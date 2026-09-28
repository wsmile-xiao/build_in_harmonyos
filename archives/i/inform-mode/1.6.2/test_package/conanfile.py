#!/usr/bin/env python3
"""Consumer test for inform-mode/1.6.2."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class InformModeTestConan(ConanFile):
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
        dep = self.dependencies["inform-mode"]
        sitedir = os.path.join(dep.package_folder, dep.cpp_info.resdirs[0])
        if not os.path.isdir(sitedir):
            raise Exception(f"inform-mode site-lisp directory not found: {sitedir}")
        if not can_run(self):
            self.output.info("Cross-built inform_mode_probe; runtime verification "
                             "is deferred to the OHOS target")
            return
        probe = os.path.join(self.cpp.build.bindir, "inform_mode_probe")
        self.run(f'"{probe}" "{sitedir}" "{dep.package_folder}"', env="conanrun")
