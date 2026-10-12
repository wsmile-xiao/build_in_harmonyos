#!/usr/bin/env python3
"""Conan test_package for imenu-list 0.9."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class ImenuListTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        script = os.path.join(self.recipe_folder, "test_imenu_list.sh")
        shell = self._shell()
        self.run(
            f"{shlex.quote(shell)} {shlex.quote(script)}",
            env="conanrun",
        )

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
