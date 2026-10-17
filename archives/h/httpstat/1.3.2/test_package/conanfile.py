#!/usr/bin/env python3
"""Consumer test for the packaged httpstat command."""

import os

from conan import ConanFile


class HttpstatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = str(self.dependencies["httpstat"].package_folder)
        httpstat = os.path.join(package_folder, "bin", "httpstat")
        test_script = os.path.join(self.recipe_folder, "test_httpstat.sh")
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(
            f'"{bash}" "{test_script}" "{httpstat}"',
            env="conanrun",
        )
