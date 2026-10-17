#!/usr/bin/env python3
"""Consumer test for ldraw-parts/2602."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LDrawPartsTestConan(ConanFile):
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
        dep = self.dependencies["ldraw-parts"]
        libdir = os.path.join(dep.package_folder, dep.cpp_info.resdirs[0])
        if not os.path.isdir(libdir):
            raise Exception(f"ldraw-parts resource directory not found: {libdir}")
        if not can_run(self):
            self.output.info("Cross-built ldraw_parts_probe; runtime verification "
                             "is deferred to the OHOS target")
            return
        probe = os.path.join(self.cpp.build.bindir, "ldraw_parts_probe")
        self.run(f'"{probe}" "{libdir}"', env="conanrun")
