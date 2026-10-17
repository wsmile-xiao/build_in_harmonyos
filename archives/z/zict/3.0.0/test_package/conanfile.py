#!/usr/bin/env python3
"""Consumer-side smoke test for the packaged zict Python module."""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class ZictTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["zict"].package_folder
        py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join(
            package_folder, "lib", py_version, "site-packages"
        )
        test_script = os.path.join(os.path.dirname(__file__), "test_zict.py")
        if not os.path.isfile(os.path.join(site_packages, "zict", "__init__.py")):
            raise ConanException(f"zict package missing under {site_packages}")
        self.run(
            f'"{sys.executable}" "{test_script}" "{site_packages}"',
            env="conanrun",
        )
