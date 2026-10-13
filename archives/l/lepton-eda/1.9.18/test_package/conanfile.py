#!/usr/bin/env python3
"""Smoke test for the packaged Lepton EDA executables."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class LeptonEdaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_lepton.sh", "sample/*"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("Cannot run lepton-eda in this environment")
            return

        bin_dir = os.path.join(
            self.dependencies["lepton-eda"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_lepton.sh")
        sample = os.path.join(self.build_folder, "sample")
        if not os.path.isdir(sample):
            # Some Conan layouts keep exports next to the source folder.
            sample = os.path.join(self.source_folder, "sample")
        shell = shutil.which("sh") or "/system/bin/sh"
        self.run(
            '"{}" "{}" "{}" "{}"'.format(shell, script, bin_dir, sample),
            env="conanrun")
