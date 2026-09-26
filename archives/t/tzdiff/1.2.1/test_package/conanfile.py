#!/usr/bin/env python3
"""Conan test_package for tzdiff 1.2.1: runs the packaged CLI with fixed start times."""
import os
import shutil

from conan import ConanFile


class TzdiffTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_tzdiff.sh")
        tzdiff = os.path.join(pkg, "bin", "tzdiff")
        self.run(f'"{bash}" "{script}" "{tzdiff}"', env="conanrun")
