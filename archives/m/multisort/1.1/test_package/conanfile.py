#!/usr/bin/env python3
"""test_package - multisort 1.1 (command-line tool, no library API).

Runs test_multisort.py against the packaged bin/multisort: A1-A3 ELF artifact
checks on every host, F1-F7 functional checks (usage, byte-exact merges of
1999 / 2026 / twelve-month logs, a 3000-byte line, missing and empty inputs)
mandatory on the aarch64 CI worker; see the script docstring for the
foreign-architecture rule. The binary path comes from the tested package only
(no PATH lookup), so the CI L1e destructive check fails once bin/ is removed.
Test logs are written below the gitignored build-release/ folder and removed
after the run.
"""
import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class MultisortTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        multisort = os.path.join(self.dependencies["multisort"].package_folder, "bin", "multisort")
        script = os.path.join(self.source_folder, "test_multisort.py")
        self.run(f'"{sys.executable}" "{script}" "{multisort}" "{self.build_folder}"', env="conanrun")
