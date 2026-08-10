#!/usr/bin/env python3
"""Conan test_package for GNU Emacs 29.1."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class EmacsTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        pkg = self.dependencies["emacs"].package_folder
        emacs = os.path.join(pkg, "bin", "emacs")
        script = os.path.join(self.recipe_folder, "test_emacs_batch.sh")
        shell = self._shell()
        self.run(f'"{shell}" "{script}" "{emacs}"', env="conanrun")

    def _shell(self):
        candidates = [
            "/bin/sh",
            "/system/bin/sh",
            os.environ.get("SHELL"),
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
            "sh",
        ]
        for candidate in candidates:
            if candidate and self._is_usable_executable(candidate):
                return candidate
        return "sh"

    def _is_usable_executable(self, path):
        return not os.path.isabs(path) or os.access(path, os.X_OK)
