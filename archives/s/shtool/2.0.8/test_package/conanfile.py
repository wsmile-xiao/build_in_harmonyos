#!/usr/bin/env python3
"""Conan test package for GNU shtool."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class ShtoolTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["shtool"]
            bin_dir = os.path.join(dep.package_folder, "usr", "bin")
            shtool = os.path.join(bin_dir, "shtool")
            env_path = f"{bin_dir}:$PATH"

            self.run(f'cd "{self.source_folder}" && PATH="{env_path}" sh test.sh', env="conanrun")
        else:
            self.output.warning("Cross-built shtool test cannot be run on this build host")
