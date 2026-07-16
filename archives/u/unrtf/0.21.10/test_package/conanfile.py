#!/usr/bin/env python3
"""Conan test_package for GNU UnRTF."""
import os

from conan import ConanFile
from conan.tools.files import copy


class UnrtfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        if self.source_folder != self.build_folder:
            copy(self, "test.sh", src=self.source_folder, dst=self.build_folder)
            copy(self, "sample.rtf", src=self.source_folder, dst=self.build_folder)

    def test(self):
        package_folder = self.dependencies["unrtf"].package_folder
        bin_dir = os.path.join(package_folder, "bin")
        conf_dir = os.path.join(package_folder, "share", "unrtf")
        test_script = os.path.join(self.build_folder, "test.sh")
        cmd = (
            f'export PATH="{bin_dir}:$PATH" && '
            f'export UNRTF_CONF_DIR="{conf_dir}" && '
            f'bash "{test_script}"'
        )
        self.run(cmd, env="conanrun", cwd=self.build_folder)
