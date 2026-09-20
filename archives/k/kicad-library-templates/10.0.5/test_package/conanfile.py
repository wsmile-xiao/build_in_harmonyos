#!/usr/bin/env python3
"""Consumer tests for kicad-library-templates/10.0.5."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KicadLibraryTemplatesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        if str(self.settings.os).lower() in ("ohos", "harmonyos"):
            toolchain.variables["OHOS_ARCH"] = (
                "x86_64" if str(self.settings.arch) == "x86_64" else "arm64-v8a"
            )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        variables = {}
        if str(self.settings.os).lower() in ("ohos", "harmonyos"):
            variables["OHOS_ARCH"] = (
                "x86_64" if str(self.settings.arch) == "x86_64" else "arm64-v8a"
            )
        cmake.configure(variables=variables)
        cmake.build()

    def test(self):
        dependency = self.dependencies["kicad-library-templates"]
        resource_root = os.path.join(
            dependency.package_folder, dependency.cpp_info.resdirs[0]
        )
        if not os.path.isdir(resource_root):
            raise Exception(f"KiCad template resource directory not found: {resource_root}")

        if not can_run(self):
            self.output.info(
                "Cross-built kicad_templates_probe; runtime verification is deferred "
                "to the HarmonyOS target"
            )
            return

        probe = os.path.join(self.cpp.build.bindir, "kicad_templates_probe")
        if os.path.isfile(probe + ".exe"):
            probe += ".exe"
        self.run(f'"{probe}" "{resource_root}"', env="conanrun")

        if str(self.settings.os).lower() in ("ohos", "harmonyos"):
            harmonyos_probe = os.path.join(
                self.cpp.build.bindir, "kicad_templates_harmonyos_probe"
            )
            if os.path.isfile(harmonyos_probe + ".exe"):
                harmonyos_probe += ".exe"
            self.run(f'"{harmonyos_probe}" "{resource_root}"', env="conanrun")
