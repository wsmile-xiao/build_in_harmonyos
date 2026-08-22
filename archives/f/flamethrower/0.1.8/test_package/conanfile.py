#!/usr/bin/env python3
"""Consumer test for flamethrower/0.1.8."""

import os

from conan import ConanFile


class FlamethrowerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(os.path.dirname(__file__), "test_flamethrower.sh")
        self.run(f'sh "{script}" "{pkg_folder}"', cwd=self.build_folder, env="conanrun")
