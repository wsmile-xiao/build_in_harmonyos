#!/usr/bin/env python3
"""Consumer test for the packaged JH71xx recovery utility."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class Jh71xxToolsTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def test(self):
        if not can_run(self):
            return

        binary = os.path.join(
            self.dependencies["jh71xx-tools"].package_folder,
            "bin",
            "jh7100-recover",
        )
        test_script = os.path.join(self.source_folder, "test_cli.sh")
        self.run(
            f'sh "{test_script}" "{binary}" "{self.settings.os}"',
            env="conanrun",
        )
