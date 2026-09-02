#!/usr/bin/env python3
"""Consumer test for the packaged abx executable."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class AbxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_abx.sh", "generate_wavs.py"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("Cannot run abx in this environment")
            return

        executable = os.path.join(
            self.dependencies["abx"].package_folder, "bin", "abx"
        )
        script = os.path.join(self.source_folder, "test_abx.sh")
        shell = shutil.which("sh") or "/system/bin/sh"
        self.run(
            f'"{shell}" "{script}" "{executable}"',
            env="conanrun",
        )
