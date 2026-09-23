#!/usr/bin/env python3
"""Consumer test for yash/2.60 (CLI shell)."""
import os
import shutil

from conan import ConanFile
from conan.tools.layout import basic_layout


class YashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        script = os.path.join(self.source_folder, "test_yash.sh")
        target = os.path.join(self.build_folder, "test_yash.sh")
        shutil.copy(script, target)
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindir
        shell = self._resolve_shell()
        self.run(f'{shell} "{target}" "{bindir}"', env="conanrun")

    @staticmethod
    def _resolve_shell():
        for candidate in ("/data/service/hnp/bin/bash", "/usr/bin/zsh",
                          "/bin/sh", "sh"):
            if os.path.isfile(candidate):
                return candidate
        return "sh"
