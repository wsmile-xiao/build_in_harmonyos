#!/usr/bin/env python3
"""Test package for clamassassin.

L1 checks:
1. clamassassin script installed under bin/ and executable
2. functional smoke test (mock clamscan/formail): clean and infected mail
   both produce the expected X-Virus-Status headers
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class ClamassassinTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies["clamassassin"]
        script = os.path.join(dep.cpp_info.bindirs[0], "clamassassin")
        if os.path.isfile(script):
            self.output.info(f"clamassassin installed at {script}")
        else:
            raise Exception(f"clamassassin not found at {script}")

        # functional test with mock clamscan/formail (see test.sh)
        test_sh = os.path.join(self.source_folder, "test.sh")
        self.run(f"sh {test_sh}", env="conanrun")
