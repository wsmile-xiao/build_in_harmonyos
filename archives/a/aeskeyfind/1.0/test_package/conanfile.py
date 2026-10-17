#!/usr/bin/env python3
"""Conan test_package for aeskeyfind 1.0."""
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.build import can_run


class AeskeyfindTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        package_folder = self.dependencies["aeskeyfind"].package_folder
        aeskeyfind = os.path.join(package_folder, "bin", "aeskeyfind")
        if not os.path.isfile(aeskeyfind):
            raise Exception(f"aeskeyfind binary not found: {aeskeyfind}")

        test_script = os.path.join(self.source_folder, "test_aeskeyfind.py")
        self.run(
            "{} {} {}".format(
                shlex.quote(sys.executable),
                shlex.quote(test_script),
                shlex.quote(aeskeyfind),
            ),
            env="conanrun",
        )
