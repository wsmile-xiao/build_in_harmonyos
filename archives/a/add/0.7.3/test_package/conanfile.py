#!/usr/bin/env python3

"""Conan consumer test for add 0.7.3 CLI executables."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class AddTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["add"].package_folder

        add_det = os.path.join(package_folder, "bin", "add-det")
        linkdupes = os.path.join(package_folder, "bin", "linkdupes")

        if not os.path.isfile(add_det):
            raise RuntimeError(f"add-det binary not found: {add_det}")

        if not os.path.isfile(linkdupes):
            raise RuntimeError(f"linkdupes binary not found: {linkdupes}")

        if can_run(self):
            script = os.path.join(
                self.recipe_folder,
                "test_add.sh",
            )

            shell = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash"
            )

            self.run(
                f'"{shell}" "{script}" "{add_det}" "{linkdupes}"',
                env="conanrun",
            )
        else:
            for binary in (add_det, linkdupes):
                with open(binary, "rb") as file_handle:
                    if file_handle.read(4) != b"\x7fELF":
                        raise RuntimeError(
                            f"Not an ELF executable: {binary}"
                        )
