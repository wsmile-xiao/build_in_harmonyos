#!/usr/bin/env python3
"""Consumer test for installation-birthday/20."""

import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class InstallationBirthdayTestConan(ConanFile):
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
        dep = self.dependencies["installation-birthday"]
        root = dep.package_folder
        script = os.path.join(root, "bin", "installation-birthday")
        if not os.path.isfile(script):
            raise Exception(
                "installation-birthday script not found under bin/: " + root)
        if not can_run(self):
            self.output.info("Cross-built installation_birthday_probe; runtime "
                             "verification is deferred to the OHOS target")
            return
        probe = os.path.join(self.cpp.build.bindir, "installation_birthday_probe")
        self.run(f'"{probe}" "{root}"', env="conanrun")

        # 运行语义断言：test_behavior.py（纯标准库，python3 或 python）
        py = shutil.which("python3") or shutil.which("python") or sys.executable
        driver = os.path.join(self.source_folder, "test_behavior.py")
        self.run(f'"{py}" "{driver}" "{script}"', env="conanrun")
