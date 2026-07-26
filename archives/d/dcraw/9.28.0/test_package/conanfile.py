#!/usr/bin/env python3
"""Conan L1 smoke test for the packaged dcraw executable."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class DcrawTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "dcraw test supports Linux and OHOS only, "
                f"got {self.settings.os}"
            )

        binary = os.path.join(
            self.dependencies["dcraw"].package_folder,
            "bin",
            "dcraw",
        )
        assert os.path.isfile(binary), f"dcraw binary not found: {binary}"

        test_script = os.path.join(self.recipe_folder, "test_dcraw.sh")
        self.run(
            f'sh "{test_script}" "{binary}"',
            env="conanrun",
        )
