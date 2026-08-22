#!/usr/bin/env python3
"""Conan recipe for ranger — A VIM-inspired filemanager for the console.

This is a pure Python package (no C/C++ compilation needed).
Build system: Python setuptools (setup.py).
Entry points: ranger, rifle (console scripts).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class RangerConan(ConanFile):
    name = "ranger"
    version = "1.9.4"
    description = "A VIM-inspired filemanager for the console"
    license = "GPL-3.0-only"
    homepage = "https://ranger.github.io/"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Ensure setuptools is available (provides distutils shim for Python 3.12+)
        self.run("python3 -m pip install --quiet setuptools wheel")
        # Build the Python package
        staging = os.path.join(self.build_folder, "staging")
        self.run(
            f"SETUPTOOLS_USE=1 python3 -m pip install . --no-deps "
            f"--no-build-isolation --target={staging}"
        )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        # Copy all installed files (Python modules + bin/ entry points)
        copy(self, "*", src=staging, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # Set PYTHONPATH so the entry-point scripts can find the modules
        self.runenv_info.define("PYTHONPATH", self.package_folder)
