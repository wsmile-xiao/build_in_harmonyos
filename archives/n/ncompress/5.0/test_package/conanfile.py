#!/usr/bin/env python3
"""Conan test_package — ncompress 5.0 consumer smoke test.

Verifies the packaged tool from a consumer point of view:
- compress -V prints the version banner
- a real compress / decompress round trip is byte-consistent
"""
import os
import shutil

from conan import ConanFile


class NcompressTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_ncompress.sh")
        self.run(f'{bash} {script} "{os.path.join(pkg_folder, "bin")}"',
                 env="conanrun")
