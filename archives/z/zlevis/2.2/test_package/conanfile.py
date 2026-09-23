#!/usr/bin/env python3
"""Conan test_package for zlevis 2.2."""
import os
import shutil

from conan import ConanFile


class ZlevisTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        sh = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "/system/bin/sh"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_zlevis.sh")
        self.run(
            f'"{sh}" "{script}" "./bin"',
            env="conanrun",
            cwd=pkg_folder,
        )