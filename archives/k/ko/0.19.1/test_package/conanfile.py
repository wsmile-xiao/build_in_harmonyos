#!/usr/bin/env python3
"""Conan test_package for ko 0.19.1 (application).

Runs three HarmonyOS consumer test cases against the packaged ko binary
(version report / subcommand surface / cobra completion path).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class KoTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["ko"].package_folder
        bin_path = os.path.join(package_folder, "bin", "ko")
        assert os.path.isfile(bin_path), f"ko binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f'{bash} "{test_script}" "{bin_path}"', env="conanrun")
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"ko is not an ELF binary: {magic!r}"
            self.output.info(f"ko binary exists and has ELF magic: {bin_path}")
