#!/usr/bin/env python3
"""test_package - sleepenh 1.8 (command-line tool, no library API).

Runs test_sleepenh.py against the tested package: A1-A4 artifact checks on
every host (ELF64 AArch64 / PIE / OHOS musl loader / man page), F1-F8
functional checks of bin/sleepenh (options, exit codes, real SIGALRM-driven
sleeps, drift-free chained calls) mandatory on the aarch64 CI worker; see
the script docstring for the foreign-architecture rule. The binary path comes
from the tested package only (no PATH lookup), so the CI L1e destructive
check fails once bin/ is removed. The script writes no files.
"""
import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class SleepenhTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["sleepenh"].package_folder
        script = os.path.join(self.source_folder, "test_sleepenh.py")
        self.run(f'"{sys.executable}" "{script}" "{package_folder}"', env="conanrun")
