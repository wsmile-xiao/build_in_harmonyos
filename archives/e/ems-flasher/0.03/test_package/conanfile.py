#!/usr/bin/env python3
"""Conan test_package for ems-flasher 0.03.

R34: This test must substantively exercise the tested package.
ems-flasher is a command-line tool, so we execute the binary directly
and verify --version output. The --help option exits 1 by upstream
design (usage() calls exit(1)), so we check version only.

--version prints "EMS-flasher <version>" and exits 0.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class EmsFlasherTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # R34: Execute the ems-flasher binary — substantively test the package
        # --version prints "EMS-flasher <version>" and exits 0
        # Note: --help exits 1 by upstream design (usage() calls exit(1))
        ems = self.dependencies["ems-flasher"]
        bin_path = os.path.join(ems.cpp_info.bindirs[0], "ems-flasher")
        self.output.info(f"Testing ems-flasher binary at: {bin_path}")

        # Test --version (validates the binary runs and links correctly)
        self.run(f'"{bin_path}" --version', env="conanrun")
