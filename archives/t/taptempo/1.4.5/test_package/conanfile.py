#!/usr/bin/env python3
"""Conan consumer test for TapTempo 1.4.5 (CLI)."""

import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TaptempoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "functional.py"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            raise ConanException("TapTempo target cannot run; package runtime test is required")
        package_folder = self.dependencies["taptempo"].package_folder
        binary = os.path.join(package_folder, "bin", "taptempo")
        report_dir = os.environ.get(
            "TAPTEMPO_REPORT_DIR",
            os.path.join(self.build_folder, "functional-results"),
        )
        command = [sys.executable,
                   os.path.join(self.source_folder, "functional.py"),
                   binary, "--report-dir", report_dir]
        self.run(" ".join(shlex.quote(arg) for arg in command), env="conanrun")
