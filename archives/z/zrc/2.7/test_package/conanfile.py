#!/usr/bin/env python3
"""Consumer test for zrc/2.7 (CLI application)."""
import os
import shutil

from conan import ConanFile
from conan.tools.layout import basic_layout


class ZrcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        script = os.path.join(self.source_folder, "test_zrc.sh")
        target = os.path.join(self.build_folder, "test_zrc.sh")
        shutil.copy(script, target)
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder,
                              dep.cpp_info.bindirs[0])
        shell = self._resolve_shell()
        self.run(f'{shell} "{target}" "{bindir}"', env="conanrun")

    @staticmethod
    def _resolve_shell():
        for candidate in ("/data/service/hnp/bin/bash", "/usr/bin/zsh",
                          "/bin/sh", "sh"):
            if os.path.isfile(candidate):
                return candidate
        return "sh"
