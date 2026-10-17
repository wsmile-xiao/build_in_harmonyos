#!/usr/bin/env python3
"""Conan test_package - bali-phy 4.1 (application: run the \x27bali-phy\x27 binary)."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class BaliPhyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.warning("bali-phy: cross-building - skipping runtime test of the target binary")
            return

        dep = self.dependencies["bali-phy"]
        bin_dir = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0])
        bp = os.path.join(bin_dir, "bali-phy")
        if not os.path.isfile(bp):
            raise ConanException("bali-phy: binary not found in package: %s" % bp)

        # Installed examples (meson install_subdir examples ->
        # <prefix>/share/doc/bali-phy/examples).
        examples = os.path.join(dep.package_folder, "share", "doc", "bali-phy", "examples")
        script = os.path.join(self.source_folder, "test_bali_phy.sh")
        self.run("sh %s %s %s" % (script, bp, examples))
