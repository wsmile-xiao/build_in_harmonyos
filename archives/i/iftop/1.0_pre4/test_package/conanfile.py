#!/usr/bin/env python3
"""Conan test_package — iftop 1.0_pre4.

iftop is a command-line tool (not a library), so the consumer test runs a
real shell test source (test.sh) that executes the installed binary in
safe, unprivileged scenarios (help output and exit codes).

R34: Test must exercise the tested package's binary.
L0c: test_package/ must contain a real, version-controlled test source file.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class IftopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Test must exercise the tested package's binary via test.sh,
        # which asserts real output and exit codes of `iftop -h`.
        if can_run(self):
            # test.sh is version-controlled inside the recipe folder; run it
            # directly (in-place test_package builds share that folder).
            test_script = os.path.join(self.recipe_folder, "test.sh")
            self.run("sh " + test_script, env="conanrun")
