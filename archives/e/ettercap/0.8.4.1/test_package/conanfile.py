#!/usr/bin/env python3
"""Conan test_package for ettercap 0.8.4.1.

R34: test must substantively exercise the tested package.
ettercap is a CLI tool, so we run its binaries (--version).
"""
import os

from conan import ConanFile


class EttercapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: substantively test by running the installed binaries
        # No can_run() guard — the binaries must be executed to verify
        # the package is genuine (L1e negative test enforces this).
        bin_dir = os.path.join(self.dependencies["ettercap"].package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test_ettercap.sh")
        self.run(
            f"bash {script} "
            f"{os.path.join(bin_dir, 'ettercap')} "
            f"{os.path.join(bin_dir, 'etterfilter')} "
            f"{os.path.join(bin_dir, 'etterlog')}",
            env="conanrun",
        )
