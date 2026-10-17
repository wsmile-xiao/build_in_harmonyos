#!/usr/bin/env python3
"""Conan test_package — debian-parl (Debian Pure Blend config/metadata package).

Honest validation of a metapackage/blend config package (no binary exists):
  - packaged layout: 3 boxer nodes/*.yml + 2 skel/*.in + Makefile/NEWS/TODO +
    debian-metadata.json + license
  - nodes reference the expected boxer classes (Task.harden.desktop,
    Desktop.locale.EU / Desktop.locale) as shipped upstream
  - debian-metadata.json records the real binary-package semantics (counts,
    profiles) of debian-parl 1.9.33+nmu1 (provenance from official .debs)
These are package/data validations; upstream blend has no test suite.
"""
import os

from conan import ConanFile


class DebianParlTestConan(ConanFile):
    settings = None
    options = None
    default_options = None

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["debian-parl"].package_folder
        script = os.path.join(self.source_folder, "test_parl.py")
        self.run(f"python3 {script} {pkg}", env="conanrun")
