#!/usr/bin/env python3
"""Conan test_package — installed comet CLI smoke test.

Upstream ships no test suite (see MANIFEST.yml); the package is verified by
exercising the installed binary's CLI surface (exact --version output,
--help usage, clap rejection of unknown flags).
"""

import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class CometTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration("The comet smoke test must run on the target")
        binary = os.path.join(self.dependencies["comet"].package_folder, "bin", "comet")
        self.run(shlex.join([sys.executable,
                             os.path.join(self.source_folder, "test_comet.py"), binary]))
