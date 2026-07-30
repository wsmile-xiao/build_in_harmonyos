#!/usr/bin/env python3
"""Conan test_package for paxrelabel 0.1.1."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class PaxrelabelTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["paxrelabel"].package_folder
        executable = os.path.join(package_folder, "bin", "paxrelabel")
        if not os.path.isfile(executable):
            raise Exception(f"Missing paxrelabel executable: {executable}")

        if not can_run(self):
            self.output.info("Cross-building; verified packaged executable exists but runtime test is skipped")
            return

        test_script = os.path.join(self.source_folder, "test_paxrelabel.sh")
        self.run(f'bash "{test_script}" "{executable}"', cwd=self.build_folder, env="conanrun")

