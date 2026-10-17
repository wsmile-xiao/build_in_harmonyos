#!/usr/bin/env python3
"""Conan test_package for vimtutor-sequel 1.3.2."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class VimtutorSequelTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg_folder = self.dependencies["vimtutor-sequel"].package_folder
            test_script = os.path.join(self.recipe_folder, "test_vimtutor_sequel.sh")
            self.run(f'sh "{test_script}" "{pkg_folder}"', env="conanrun")
