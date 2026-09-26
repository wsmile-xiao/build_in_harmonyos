#!/usr/bin/env python3
"""Consumer test for kicad-library-packages3d/10.0.5."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KicadLibraryPackages3dTestConan(ConanFile):
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
        dep = self.dependencies["kicad-library-packages3d"]
        models_root = os.path.join(dep.package_folder, dep.cpp_info.resdirs[0])
        if not os.path.isdir(models_root):
            raise Exception(f"kicad-library-packages3d resource directory not found: {models_root}")
        if not can_run(self):
            self.output.info("Cross-built kicad_packages3d_probe; runtime verification "
                             "is deferred to the OHOS target")
            return
        probe = os.path.join(self.cpp.build.bindir, "kicad_packages3d_probe")
        self.run(f'"{probe}" "{models_root}"', env="conanrun")
