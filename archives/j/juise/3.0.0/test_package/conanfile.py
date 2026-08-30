#!/usr/bin/env python3
"""Conan test_package for juise 3.0.0.

Verifies the juise and juise-askpass command-line tools are installed and
executable, and that juise --version reports version information.
"""
import os
import shutil

from conan import ConanFile


class JuiseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        sh = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "/bin/sh"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_juise.sh")
        self.run(f'{sh} "{script}" "{pkg_folder}"',
                 env="conanrun")
