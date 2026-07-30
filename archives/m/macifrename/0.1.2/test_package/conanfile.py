#!/usr/bin/env python3
"""Consumer test package for macifrename."""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class MacifrenameTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindirs = self.dependencies["macifrename"].cpp_info.bindirs
        executable = os.path.join(bindirs[0], "macifrename")
        if not os.path.isfile(executable):
            raise ConanException(f"missing packaged executable: {executable}")

        if not can_run(self):
            self.output.info("cross build: packaged executable exists; runtime checks skipped")
            return

        test_script = os.path.join(self.source_folder, "test_macifrename.py")
        self.run(f'"{sys.executable}" "{test_script}" "{executable}"', env="conanrun")
