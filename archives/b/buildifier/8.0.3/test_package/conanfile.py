#!/usr/bin/env python3

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class BuildifierTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["buildifier"].package_folder
        bin_path = os.path.join(package_folder, "bin", "buildifier")

        assert os.path.isfile(bin_path), f"buildifier binary not found: {bin_path}"

        if can_run(self):
            shell = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash"
            )
            script = os.path.join(self.recipe_folder, "test_buildifier.sh")
            self.run(
                f'"{shell}" "{script}" "{bin_path}"',
                env="conanrun",
            )
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)

            assert magic == b"\x7fELF", (
                f"buildifier is not an ELF binary: {magic!r}"
            )
            self.output.info(
                f"buildifier binary exists and has ELF magic: {bin_path}"
            )
