#!/usr/bin/env python3
"""Conan test_package — mrbayes 3.2.7a (application: run the 'mb' binary)"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class MrbayesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.warning(
                "mrbayes: cross-building — skipping runtime test of the target binary"
            )
            return

        # Locate the installed binary through the package metadata so that
        # the test genuinely depends on the package artifacts.
        dep = self.dependencies["mrbayes"]
        bin_dir = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0])
        mb = os.path.join(bin_dir, "mb")
        if not os.path.isfile(mb):
            raise ConanException(f"mrbayes: binary not found in package: {mb}")

        script = os.path.join(self.source_folder, "test_mb.sh")
        self.run(f'sh "{script}" "{mb}"')
