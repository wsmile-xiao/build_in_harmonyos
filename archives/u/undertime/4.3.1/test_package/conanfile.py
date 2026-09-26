#!/usr/bin/env python3
"""Conan test_package for undertime — real consumer verification (R34 / PF3).

Consumes the installed ``undertime`` package and actually executes its
packaged console script plus the vendored runtime imports. Nothing here is a
print-only stub.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class UndertimeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["undertime"].package_folder
        maj, minr = sys.version_info[:2]
        bindir = os.path.join(pkg, "bin")
        site = os.path.join(pkg, "lib", f"python{maj}.{minr}", "site-packages")
        if not os.path.isdir(bindir):
            raise ConanException(f"package bin/ directory missing: {bindir}")
        if not os.path.isdir(site):
            raise ConanException(f"package site-packages missing: {site}")

        script = os.path.join(self.source_folder, "test_undertime_pkg.py")
        if not os.path.isfile(script):
            raise ConanException(f"test_undertime_pkg.py missing: {script}")

        # Real execution of the packaged tools (L0d/PF3: non-empty test).
        self.run(f'"{sys.executable}" "{script}" "{bindir}" "{site}"')
