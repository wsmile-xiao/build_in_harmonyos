#!/usr/bin/env python3
"""Conan consumer test for lemmeknow 0.8.0 (Rust binary package).

Two layers of verification:

  1. package integrity — the packaged `lemmeknow` executable exists;
  2. consumer smoke + HarmonyOS traits — test_lemmeknow.py runs the binary,
     asserts AArch64 / musl loader / OHOS code signature, then exercises the
     actual identification functionality (--help / --version / pattern
     identification of an IP address).
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LemmeknowTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_lemmeknow.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["lemmeknow"].package_folder
        exe = os.path.join(package_folder, "bin", "lemmeknow")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing lemmeknow executable: {exe}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_lemmeknow.py")
        result = self.run(
            f'PACKAGE_FOLDER="{package_folder}" "{sys.executable}" "{script}"',
            env="conanrun",
            ignore_errors=True,
        )
        if result != 0:
            raise AssertionError(
                f"lemmeknow test_package failed with exit code {result}"
            )
