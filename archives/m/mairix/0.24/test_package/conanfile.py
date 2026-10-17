#!/usr/bin/env python3
"""Consumer test for mairix/0.24 (CLI application)."""
import os
import shutil

from conan import ConanFile
from conan.tools.layout import basic_layout


class MairixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        script = os.path.join(self.source_folder, "test_mairix.sh")
        target = os.path.join(self.build_folder, "test_mairix.sh")
        shutil.copy(script, target)
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        bindir = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            bindir)
        shell = self._resolve_shell()
        self.run(f'{shell} "{target}" "{bindir}"', env="conanrun")

    @staticmethod
    def _resolve_shell():
        for candidate in ("/data/service/hnp/bin/bash", "/usr/bin/zsh",
                          "/bin/sh", "sh"):
            if os.path.isfile(candidate):
                return candidate
        return "sh"
