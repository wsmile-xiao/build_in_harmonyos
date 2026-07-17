#!/usr/bin/env python3
"""Smoke tests for the po4a Conan package."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class Po4aTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        bin_dir = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "bin")
        lib_dir = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "lib", "perl5")
        self.output.info(f"po4a bin dir: {bin_dir}")
        self.output.info(f"po4a perl lib dir: {lib_dir}")

        for name in ("po4a", "po4a-gettextize", "po4a-translate", "po4a-updatepo", "msguntypot"):
            path = os.path.join(bin_dir, name)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(f"missing packaged script: {name}")

        module = os.path.join(lib_dir, "Locale", "Po4a", "Po.pm")
        if not os.path.isfile(module):
            raise ConanInvalidConfiguration("missing Locale::Po4a::Po module")

        if can_run(self):
            self.run(
                'perl -MLocale::Po4a::Po -e \'print "Locale::Po4a::Po loaded\\n"\'',
                env="conanrun",
            )
            self.run("po4a --version", env="conanrun")
