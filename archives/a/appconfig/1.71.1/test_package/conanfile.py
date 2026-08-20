#!/usr/bin/env python3
"""Consumer test for appconfig/1.71.1."""

import os

from conan import ConanFile


class AppConfigTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(os.path.dirname(__file__), "test_appconfig.sh")
        self.run(f'sh "{script}"', cwd=self.build_folder, env="conanrun")
