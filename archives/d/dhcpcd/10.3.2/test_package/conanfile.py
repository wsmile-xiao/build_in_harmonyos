#!/usr/bin/env python3
"""Conan test_package for dhcpcd 10.3.2.

Verifies installed dhcpcd binary exists and runs --version / -V.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class DhcpcdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["dhcpcd"].package_folder
        # dhcpcd 装到 sbin/ 或 bin/
        bindir = None
        for cand in (os.path.join(pkg, "sbin"), os.path.join(pkg, "bin")):
            if os.path.isfile(os.path.join(cand, "dhcpcd")):
                bindir = cand
                break
        if bindir is None:
            raise SystemExit("FAIL: dhcpcd binary missing (sbin/ or bin/)")
        self.output.info(f"OK: dhcpcd present in {bindir}")
        script = os.path.join(self.source_folder, "test_dhcpcd.sh")
        if cross_building(self):
            self.output.info("cross-building: only verifying test script + binary present")
            if not os.path.isfile(script):
                raise SystemExit("FAIL: test_dhcpcd.sh missing")
            return
        self.run(f"sh {script} {bindir}", env="conanrun")
