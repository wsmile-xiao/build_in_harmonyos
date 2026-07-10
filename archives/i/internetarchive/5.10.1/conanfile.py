#!/usr/bin/env python3
"""Conan recipe for internetarchive 5.10.1 — Python package (setuptools).

This is a pure Python package providing a Python interface to archive.org.
It includes a CLI tool `ia` and the `internetarchive` Python library.

Build system: setuptools (setup.py + setup.cfg)
No C/C++ compilation required — pure Python wheel (py3-none-any).
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class InternetarchiveConan(ConanFile):
    name = "internetarchive"
    version = "5.10.1"
    description = "A Python interface to archive.org."
    license = "AGPL-3.0"
    homepage = "https://github.com/jjjake/internetarchive"
    url = ""

    # R32: settings.os check must use in ("Linux", "OHOS")
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Python dependencies are installed via pip in build(), not as Conan requires
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches (none currently, but required by G1 check)
        apply_conandata_patches(self)

        # Use sys.executable to get the full python path (conan build env may not have pip in PATH)
        python_exe = sys.executable

        # Step 1: Install Python dependencies needed by internetarchive
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            '"jsonpatch>=0.4" '
            '"requests>=2.25.0,<3.0.0" '
            '"tqdm>=4.0.0" '
            '"urllib3>=1.26.0"',
            env="conanrun",
        )

        # Step 2: Build and install the package to the package folder
        src_dir = self.source_folder
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{self.package_folder}" "{src_dir}"',
            env="conanrun",
        )

    def package(self):
        # Files already installed to package_folder in build() via --prefix
        pass

    def package_info(self):
        # Set up environment for consumers
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join("lib", py_ver, "site-packages")

        # Add bin to PATH
        self.cpp_info.bindirs = ["bin"]
        # Add Python lib path
        self.cpp_info.libdirs = [site_packages]

        # Set environment variables for consumers
        bin_path = os.path.join(self.package_folder, "bin")
        lib_path = os.path.join(self.package_folder, site_packages)
        self.runenv_info.define("PATH", bin_path)
        self.runenv_info.define("PYTHONPATH", lib_path)
