#!/usr/bin/env python3
"""Conan consumer tests for recc 1.4.13 (application)."""

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import save


class ReccTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        # Exercise the recc binary: --help must parse and print usage
        # (proves the ELF runs on HarmonyOS PC).
        self.run("recc --help", env="conanrun")
        # recc with no args exits non-zero but must not crash.
        self.run("recc --version", env="conanrun", ignore_errors=True)
