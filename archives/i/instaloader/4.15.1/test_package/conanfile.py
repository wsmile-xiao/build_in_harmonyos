#!/usr/bin/env python3
"""Conan consumer tests for the instaloader 4.15.1 setuptools package."""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class InstaloaderTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join(
            package, "lib", python_version, "site-packages"
        )
        launcher = os.path.join(package, "bin", "instaloader")
        smoke = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke.py")

        if not os.path.isdir(os.path.join(site_packages, "instaloader")):
            raise ConanException("instaloader package directory is missing")
        if not os.path.isfile(launcher) or not os.access(launcher, os.X_OK):
            raise ConanException("instaloader launcher is missing or not executable")

        old_pythonpath = os.environ.get("PYTHONPATH")
        explicit_pythonpath = site_packages + (
            os.pathsep + old_pythonpath if old_pythonpath else ""
        )
        os.environ["PYTHONPATH"] = explicit_pythonpath
        try:
            if self.run(
                f'PYTHONPATH="{explicit_pythonpath}" python3 "{smoke}" "{site_packages}"'
            ) != 0:
                raise ConanException("consumer API smoke test failed")
            if self.run(
                f'PYTHONPATH="{explicit_pythonpath}" "{launcher}" --version'
            ) != 0:
                raise ConanException("instaloader --version failed")
        finally:
            if old_pythonpath is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old_pythonpath
