#!/usr/bin/env python3
"""Conan consumer test for rumdl 0.2.39 (Rust binary package).

Two layers of verification:

  1. package integrity — the packaged `rumdl` executable exists;
  2. consumer smoke + HarmonyOS traits — test_rumdl.py runs the binary,
     asserts AArch64 / musl loader / OHOS code signature, then exercises the
     real functionality (`--version` / `--help`, a lint `check` run that must
     report a rule violation, and a `fmt` run that must rewrite the file).
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class RumdlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_rumdl.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["rumdl"].package_folder
        exe = os.path.join(package_folder, "bin", "rumdl")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing rumdl executable: {exe}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_rumdl.py")
        result = self.run(
            f'PACKAGE_FOLDER="{package_folder}" "{sys.executable}" "{script}"',
            env="conanrun",
            ignore_errors=True,
        )
        if result != 0:
            raise AssertionError(
                f"rumdl test_package failed with exit code {result}"
            )
