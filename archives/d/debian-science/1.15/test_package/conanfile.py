#!/usr/bin/env python3
"""Conan test_package — debian-science (Debian Pure Blend metadata package).

Honest validation (no compiled binary exists to run):
  - packaged file layout (46 task files, tasksel desc, registry.json, snapshot, license)
  - tasks/*.Deb822 structure, tasksel desc structure (1 parent + 41 science-* keys)
  - registry.json re-derived from the packaged files (cross-check, not a tautology)
  - debian/control declared packages (45, all Architecture: all, all science-*)
  - official dependency snapshot topic set == tasks/ file set
Upstream blend ships no test suite, so these are package/data validations.
"""
import os

from conan import ConanFile


class DebianScienceTestConan(ConanFile):
    settings = None
    options = None
    default_options = None

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["debian-science"].package_folder
        script = os.path.join(self.source_folder, "test_debian_science.py")
        self.run("python3 %s %s" % (script, pkg), env="conanrun")
