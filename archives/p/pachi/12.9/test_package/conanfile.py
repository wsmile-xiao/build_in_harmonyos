#!/usr/bin/env python3
"""Conan test_package for pachi 12.9 - CLI tool test.

Runs test.sh which checks --version/help output and a real GTP genmove.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PachiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["pachi"]
            bin_path = os.path.join(dep.package_folder, "bin", "pachi")
            test_script = os.path.join(self.source_folder, "test.sh")
            self.run('sh "%s" "%s"' % (test_script, bin_path), env="conanrun")
