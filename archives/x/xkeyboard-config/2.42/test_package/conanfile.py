#!/usr/bin/env python3
"""Conan test_package — xkeyboard-config 2.42 (data-only consumer validation).

Data-only XKB configuration package: no libraries or binaries to link/run.
The test() method runs a Python consumer check (test_package.py) that
verifies the installed XKB data is complete and discoverable:
  - rules/base.xml, rules/evdev.xml exist
  - rules/base.lst, rules/evdev.lst exist
  - symbols/, keycodes/, compat/, types/, geometry/ directories exist
  - pkg-config file (xkeyboard-config.pc) is installed and resolvable
"""
import os

from conan import ConanFile


class XkeyboardConfigTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["xkeyboard-config"]
        pkg_folder = dep.package_folder
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_package.py")
        self.run(f'python3 "{script}" "{pkg_folder}"', env="conanrun")
