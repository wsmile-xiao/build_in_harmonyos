#!/usr/bin/env python3
"""Consumer test for kicad-library/3d-10.0.5."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KicadLibrary3dTestConan(ConanFile):
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
        dep = self.dependencies["kicad-library"]
        resource_root = os.path.join(dep.package_folder, dep.cpp_info.resdirs[0])
        if not os.path.isdir(resource_root):
            raise Exception(f"kicad-library resource directory not found: {resource_root}")
        if not can_run(self):
            self.output.info(
                "Cross-built kicad_library_3d_probe; runtime verification is deferred "
                "to the OHOS target"
            )
            return
        probe = os.path.join(self.cpp.build.bindir, "kicad_library_3d_probe")
        ohos_flag = " --require-ohos" if str(self.settings.os) == "OHOS" else ""
        self.run(f'"{probe}" "{resource_root}"{ohos_flag}', env="conanrun")
