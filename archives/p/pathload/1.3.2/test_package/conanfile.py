#!/usr/bin/env python3
"""Consumer tests for the pathload Conan package."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class PathloadTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        package_folder = self.dependencies["pathload"].package_folder
        bin_dir = os.path.join(package_folder, "bin")
        snd = os.path.join(bin_dir, "pathload_snd")
        rcv = os.path.join(bin_dir, "pathload_rcv")

        if not os.path.isfile(snd):
            raise RuntimeError(f"Missing executable: {snd}")
        if not os.path.isfile(rcv):
            raise RuntimeError(f"Missing executable: {rcv}")

        if not can_run(self):
            self.output.info("Skipping runtime checks while cross-building")
            return

        script = os.path.join(self.source_folder, "test_pathload.py")
        self.run(f'"{sys.executable}" "{script}" "{snd}" "{rcv}"', env="conanrun")
