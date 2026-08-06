#!/usr/bin/env python3
"""Conan test_package — abs-guide 10 L1 smoke test.

Asserts the packaged HTML documentation exists in share/doc/abs-guide/,
is complete (140 pages) and non-empty.
"""

from conan import ConanFile


class AbsGuideTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["abs-guide"]
        pkg_folder = dep.package_folder
        self.run(f"python3 test_abs_guide.py {pkg_folder}", env="conanrun")
