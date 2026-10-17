#!/usr/bin/env python3
"""Conan test_package — rsem 1.3.3 functional smoke test runner."""
import os
import platform
import subprocess

from conan import ConanFile


class RsemTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = os.path.join(self.dependencies["rsem"].cpp_info.bindirs[0])
        script = os.path.join(os.path.dirname(__file__), "test_rsem.py")
        self.run(f"python3 {script} {bindir}")
