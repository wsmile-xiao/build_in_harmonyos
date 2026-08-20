#!/usr/bin/env python3
"""Conan test_package for qbs 3.1.1-r1 — Verify binary tool works."""
from conan import ConanFile
import os


class QbsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        qbs_path = os.path.join(self.dependencies["qbs"].package_folder, "bin", "qbs")
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} test.sh {qbs_path}", env="conanrun")