#!/usr/bin/env python3
"""Conan recipe for gallery-dl 1.32.1 — Python CLI tool (setuptools).

gallery-dl is a command-line program to download image galleries and
collections from several image hosting sites.

Build system: setuptools (setup.py + pyproject.toml)
No C/C++ compilation required — pure Python.
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GallerydlConan(ConanFile):
    name = "gallery-dl"
    version = "1.32.1"
    description = "Command-line program to download image galleries and collections from several image hosting sites"
    license = "GPL-2.0-only"
    homepage = "https://github.com/mikf/gallery-dl"
    url = ""

    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Python dependencies are installed via pip in build(), not as Conan requires
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        python_exe = sys.executable

        # Step 1: Install Python runtime dependency: requests
        # Using pip without --prefix to avoid PIP_TARGET conflict
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            '"requests>=2.11.0" --quiet 2>&1',
        )

        # Step 2: Build the package
        self.run(
            f'{python_exe} setup.py build',
            cwd=self.source_folder,
        )

    def package(self):
        python_exe = sys.executable

        # Install using setup.py (not pip) to avoid PIP_TARGET/--prefix conflict
        self.run(
            f'{python_exe} setup.py install --prefix="{self.package_folder}"',
            cwd=self.source_folder,
        )

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join("lib", py_ver, "site-packages")

        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = [site_packages]

        bin_path = os.path.join(self.package_folder, "bin")
        lib_path = os.path.join(self.package_folder, site_packages)
        self.runenv_info.append_path("PATH", bin_path)
        self.runenv_info.append_path("PYTHONPATH", lib_path)
