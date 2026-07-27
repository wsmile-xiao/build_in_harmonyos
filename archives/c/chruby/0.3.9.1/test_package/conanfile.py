#!/usr/bin/env python3
"""Conan test_package for chruby 0.3.9 — Shell script test.

Verifies that chruby-exec is functional after installation.
Runs chruby-exec --version and --help.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class ChrubyTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["chruby"]
            bin_dir = os.path.join(dep.package_folder, "bin")

            bash_path = (
                os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL")
                or shutil.which("bash")
                or "/usr/local/bin/bash"
            )

            self.run(
                f'cd "{self.source_folder}" && '
                f'CONFIG_SHELL="{bash_path}" '
                f'"{bash_path}" test.sh "{bin_dir}"',
                env="conanrun"
            )
