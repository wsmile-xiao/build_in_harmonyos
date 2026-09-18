#!/usr/bin/env python3
"""Conan test_package for lddtree — real consumer verification (R34 / PF3).

Consumes the installed ``lddtree`` package and actually executes the packaged
tool (bin/lddtree.sh) against real ELF binaries and purpose-built fixtures.
Nothing here is a print-only stub.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class LddtreeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["lddtree"].package_folder
        bindir = os.path.join(pkg, "bin")
        tool = os.path.join(bindir, "lddtree.sh")
        if not os.path.isfile(tool):
            raise ConanException(f"packaged tool missing: {tool}")

        script = os.path.join(self.source_folder, "test_lddtree.py")
        if not os.path.isfile(script):
            raise ConanException(f"test_lddtree.py missing: {script}")

        # Real execution of the packaged script (L0d/PF3: non-empty test).
        # The script is invoked through the platform /bin/sh, and it runs
        # lddtree.sh with an explicit PATH carrying a binutils backend.
        import sys
        self.run(f'"{sys.executable}" "{script}" "{tool}"')
