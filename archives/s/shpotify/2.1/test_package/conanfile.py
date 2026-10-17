#!/usr/bin/env python3
"""Conan test_package for shpotify 2.1 — Shell script smoke test.

Verifies that the installed `spotify` command is functional by exercising its
real entry point: invoking it with no arguments prints usage and exits 0
(R34: the test runs the package's binary, not a stub).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class ShpotifyTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["shpotify"]
            bin_dir = os.path.join(dep.package_folder, "bin")

            bash_path = (
                os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash"
            )

            self.run(
                f'cd "{self.source_folder}" && '
                f'CONFIG_SHELL="{bash_path}" '
                f'"{bash_path}" test.sh "{bin_dir}"',
                env="conanrun",
            )
