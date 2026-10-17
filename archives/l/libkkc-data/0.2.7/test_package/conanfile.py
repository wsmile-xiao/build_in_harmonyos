#!/usr/bin/env python3
"""Conan test_package for libkkc-data — model data verification test.

libkkc-data is a data-only package; the consumer-facing API is the set of
generated binary model files under lib/libkkc/models/sorted3/. This test
verifies every shipped model file exists and matches the byte-, size- and
SHA256-exact reference (model generation is deterministic).
"""
import os
import sys

from conan import ConanFile


class LibkkcDataTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["libkkc-data"]
        self.run('"{python}" "{script}" "{root}"'.format(
                     python=sys.executable,
                     script=os.path.join(self.recipe_folder, "test_verify.py"),
                     root=pkg.package_folder))