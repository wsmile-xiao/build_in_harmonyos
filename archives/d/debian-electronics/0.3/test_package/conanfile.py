#!/usr/bin/env python3
"""Conan test_package — debian-electronics (Debian Pure Blend metadata package).

Honest validation (no compiled binary exists to run):
  - packaged file layout (13 task files, tasksel desc, registry.json, snapshot, license)
  - tasks/*.Deb822 structure (NEW blends 1.1 format with 'Format:' header), tasksel
    desc structure (1 parent + 13 electronics-* keys)
  - registry.json re-derived from the packaged files (cross-check, not a tautology)
  - debian/control declared packages (15, all Architecture: all, all electronics-*)
  - official dependency snapshot (0.2) topic set == tasks/ file set; naming rules
  - semantics: new-format mapping (no Depends lowering), genblends apt demotions,
    conan_requires == none
Upstream blend ships no test suite, so these are package/data validations.
"""
import os
import shlex

from conan import ConanFile


class DebianElectronicsTestConan(ConanFile):
    settings = None
    options = None
    default_options = None

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["debian-electronics"].package_folder
        script = os.path.join(self.source_folder, "test_debian_electronics.py")
        # shlex.quote: 路径可能含空格/括号（如本工作区 '(2)'），shell 执行需安全引用
        self.run("python3 %s %s" % (shlex.quote(script), shlex.quote(pkg)),
                 env="conanrun")
