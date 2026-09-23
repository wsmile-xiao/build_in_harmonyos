#!/usr/bin/env python3
"""Consumer test for GNU termutils 2.0 (tool package).

termutils ships no linkable public API — tput/tabs are the product, so the
consumer test executes the packaged binaries and asserts observable
behaviour (R34/R51) through test_termutils.sh.
"""
import os

from conan import ConanFile


class TermutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        script = os.path.join(self.source_folder, "test_termutils.sh")
        self.run(f'sh "{script}" "{bindir}"')
