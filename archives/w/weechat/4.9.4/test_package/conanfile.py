#!/usr/bin/env python3
"""Conan consumer test for the WeeChat chat client."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class WeechatTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Skipping weechat runtime test in a non-runnable configuration"
            )
            return

        package_folder = self.dependencies["weechat"].package_folder
        script = os.path.join(self.source_folder, "test_weechat.py")
        self.run(
            f'"{sys.executable}" "{script}" "{package_folder}" '
            f'"{self.build_folder}"',
            env="conanrun",
        )
