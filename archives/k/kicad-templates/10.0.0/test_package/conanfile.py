#!/usr/bin/env python3
"""Conan consumer test for the kicad-templates 10.0.0 resource package."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KicadTemplatesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dependency = self.dependencies[self.tested_reference_str]
        template_root = os.path.join(
            dependency.package_folder, "share", "kicad", "template"
        )
        executable = "kicad_templates_probe"
        if str(self.settings.os) == "Windows":
            executable += ".exe"
        probe = os.path.join(
            self.build_folder, self.cpp.build.bindirs[0], executable
        )
        probe = os.path.normpath(probe)
        command = f'"{probe}" "{template_root}"'
        if can_run(self):
            self.run(command, env="conanrun")
            return

        runner = os.getenv("KICAD_TEMPLATES_VM_RUNNER")
        if not runner:
            raise ConanInvalidConfiguration(
                "cross-built OHOS test requires KICAD_TEMPLATES_VM_RUNNER "
                "to execute the consumer in a native VM"
            )
        self.run(f'{runner} {command}')
