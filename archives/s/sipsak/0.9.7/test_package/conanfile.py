#!/usr/bin/env python3
"""Runtime test for the packaged sipsak command."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class SipsakTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test_sipsak.sh")
            package_folder = self.dependencies["sipsak"].package_folder
            self.run(
                'bash "{}" "{}"'.format(script, package_folder),
                env="conanrun",
            )
