#!/usr/bin/env python3
"""Consumer test for GNU dominion 2.8.2 (tool package).

dominion ships five CLI tools; the consumer test executes the packaged
binaries and asserts observable behaviour (R34/R51) through
test_dominion.sh — binary completeness plus the deterministic
invalid-option exit path of the game's getopt front end.
"""
import os

from conan import ConanFile


class DominionTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        script = os.path.join(self.source_folder, "test_dominion.sh")
        self.run(f'sh "{script}" "{bindir}"')
