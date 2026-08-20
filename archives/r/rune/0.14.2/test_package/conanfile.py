#!/usr/bin/env python3
"""Conan consumer test for the Rune command-line interpreter."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class RuneTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _shell():
        for candidate in (
            "/usr/bin/zsh",
            "/bin/zsh",
            "/data/service/hnp/bin/zsh",
            "zsh",
        ):
            if not os.path.isabs(candidate) or os.access(candidate, os.X_OK):
                return candidate
        return "zsh"

    def test(self):
        package_folder = self.dependencies["rune"].package_folder
        executable = os.path.join(package_folder, "bin", "rune")
        assert os.path.isfile(executable), f"rune binary not found: {executable}"

        if can_run(self):
            shell = self._shell()
            script = os.path.join(self.recipe_folder, "test.sh")
            self.run(
                f"{shlex.quote(shell)} {shlex.quote(script)} "
                f"{shlex.quote(executable)}",
                env="conanrun",
            )
        else:
            with open(executable, "rb") as binary:
                assert binary.read(4) == b"\x7fELF", "rune is not an ELF binary"
