#!/usr/bin/env python3
"""Conan test_package — adwaita-icon-theme 50.0 (data-only consumer validation).

Data-only icon theme package: no libraries or binaries to link/run.
The test() method runs a Python consumer check (test_package.py) that
verifies the installed theme data is complete and discoverable:
  - index.theme exists
  - Adwaita icon directories (16x16/scalable/symbolic/cursors) exist
  - representative SVG / PNG files exist
  - cursor symlinks (e.g. default -> left_ptr) exist
  - dataonly pkg-config file (adwaita-icon-theme.pc) is installed and
    resolvable via PKG_CONFIG_PATH
"""
import os

from conan import ConanFile


class AdwaitaIconThemeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["adwaita-icon-theme"]
        pkg_folder = dep.package_folder
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_package.py")
        self.run(f'python3 "{script}" "{pkg_folder}"', env="conanrun")
