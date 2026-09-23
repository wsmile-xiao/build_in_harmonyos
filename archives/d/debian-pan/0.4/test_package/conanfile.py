#!/usr/bin/env python3
"""Conan test_package — debian-pan (Debian Pure Blend metadata package).

Honest validation (no compiled binary exists to run):
  - packaged file layout (18 task files, tasksel desc, registry.json, snapshot, license)
  - tasks/* Deb822 structure (blends 1.1 Format header, Task == filename, non-empty Description)
  - tasksel desc structure (17 paragraphs = parent debian-pan + 16 pan-* keys)
  - registry.json re-derived from the packaged files (cross-check, not a tautology)
  - debian/control declared packages (18, all Architecture: all, all pan-*)
  - official dependency snapshot topic set == tasks/ file set, 5 array fields per topic
  - blends 1.1 new-format semantics recorded (file Recommends -> metapackage Recommends)
Upstream blend ships no test suite, so these are package/data validations.
"""
import os
import re
import json

from conan import ConanFile


class DebianPanTestConan(ConanFile):
    settings = None
    options = None
    default_options = None

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["debian-pan"].package_folder
        script = os.path.join(self.source_folder, "test_debian_pan.py")
        self.run("python3 %s %s" % (script, pkg), env="conanrun")
