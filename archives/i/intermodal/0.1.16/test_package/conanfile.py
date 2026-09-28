#!/usr/bin/env python3
"""Conan consumer test for intermodal 0.1.16 (Rust binary package).

Runs the packaged `imdl` executable through test_imdl.py:

  1. package integrity — the packaged `imdl` executable exists;
  2. consumer smoke + functional torrent workflow + HarmonyOS traits —
     test_imdl.py runs the binary and asserts create/info/verify/link
     behavior plus AArch64 / musl loader / OHOS code signature.
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class IntermodalTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_imdl.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["intermodal"].package_folder
        exe = os.path.join(package_folder, "bin", "imdl")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing imdl executable: {exe}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_imdl.py")
        result = self.run(
            f'PACKAGE_FOLDER="{package_folder}" "{sys.executable}" "{script}"',
            env="conanrun",
            ignore_errors=True,
        )
        if result != 0:
            raise AssertionError(
                f"intermodal test_package failed with exit code {result}")
