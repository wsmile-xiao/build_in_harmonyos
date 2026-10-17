#!/usr/bin/env python3
"""Consumer test for kicad-demos/10.0.4."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KicadDemosTestConan(ConanFile):
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
        dep = self.dependencies["kicad-demos"]
        demos_root = os.path.join(dep.package_folder, dep.cpp_info.resdirs[0])
        if not os.path.isdir(demos_root):
            raise Exception(f"kicad-demos resource directory not found: {demos_root}")
        if not can_run(self):
            self.output.info("Cross-built kicad_demo_probe; runtime verification "
                             "is deferred to the OHOS target")
            return
        probe = os.path.join(self.cpp.build.bindir, "kicad_demo_probe")
        self.run(f'"{probe}" "{demos_root}"', env="conanrun")
