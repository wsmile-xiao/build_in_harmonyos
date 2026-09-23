#!/usr/bin/env python3
"""Conan test_package - uusi 0.4.4.0.

The consumer test exercises the three shipped executables:
- uusi-extract: read package name/version from a cabal file
- uusi: semantic cabal rewrite in place
- gen-setup: generate a boilerplate Setup.hs
"""
import os
from pathlib import Path

from conan import ConanFile


class UusiTestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def configure(self):
        self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_root = None
        try:
            dep = self.dependencies.get("uusi")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(f"Could not get uusi package_folder via dependencies API: {e}")

        test_script = Path(__file__).parent / "test_uusi.sh"
        if pkg_root:
            os.environ["UUSI_PKG_ROOT"] = str(pkg_root)
        self.run(f"sh {test_script}")
