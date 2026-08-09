#!/usr/bin/env python3
"""Conan L1 smoke tests for the packaged iputils commands."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class IputilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["iputils"].package_folder
        if not can_run(self):
            # Cross-compiled context (x86_64 CI worker): verify the packaged
            # commands exist without trying to execute aarch64 binaries.
            for command in ("ping", "tracepath", "arping", "clockdiff"):
                if not os.path.isfile(os.path.join(package_folder, "bin", command)):
                    raise ConanException(
                        f"packaged command missing: {command}"
                    )
            return
        test_script = os.path.join(self.recipe_folder, "test_iputils.sh")
        self.run(f'sh "{test_script}" "{package_folder}"', env="conanrun")
