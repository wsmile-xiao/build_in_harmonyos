#!/usr/bin/env python3
"""Conan test_package for udiskie 2.6.2 — real consumer verification (R34/PF3).

Consumes the installed ``udiskie`` package and actually executes checks against
it (no print-only stub): imports the packaged Python package, exercises the
real config/matcher logic (with the vendored PyYAML), re-runs the upstream
device-matching scenarios, executes the packaged launchers and validates the
OHOS-specific packaging.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class UdiskieTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["udiskie"].package_folder
        maj, minr = sys.version_info[:2]
        site = os.path.join(pkg, "lib", f"python{maj}.{minr}", "site-packages")
        bindir = os.path.join(pkg, "bin")
        if not os.path.isdir(bindir):
            raise ConanException(f"package bin/ directory missing: {bindir}")
        if not os.path.isdir(site):
            raise ConanException(f"package site-packages missing: {site}")

        script = os.path.join(os.path.dirname(__file__), "test_udiskie_pkg.py")
        if not os.path.isfile(script):
            raise ConanException(f"test_udiskie_pkg.py missing: {script}")

        # Real execution of the packaged artefacts (L0d/PF3: non-empty test).
        self.run(f'"{sys.executable}" "{script}" "{pkg}" "{site}"')
