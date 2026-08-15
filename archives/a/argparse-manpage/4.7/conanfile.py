#!/usr/bin/env python3
"""Conan recipe for argparse-manpage — Python tool to generate man pages.

This is a pure Python package (no C/C++ compilation needed).
Build system: Python setuptools (setup.py + pyproject.toml).
Entry point: argparse-manpage (console_scripts).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class ArgparseManpageConan(ConanFile):
    name = "argparse-manpage"
    version = "4.7"
    description = "Build manual page from Python's ArgumentParser object"
    license = "Apache-2.0"
    homepage = "https://github.com/praiskup/argparse-manpage"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Ensure build backend is available (--no-build-isolation requires it)
        self.run("python3 -m pip install --quiet setuptools wheel")
        # Install the Python package to a staging directory using pip
        staging = os.path.join(self.build_folder, "staging")
        self.run(
            f"python3 -m pip install . --no-deps --no-build-isolation "
            f"--target={staging}"
        )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        # Copy all installed files (Python modules + bin/ entry point)
        copy(self, "*", src=staging, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # Set PYTHONPATH so the entry-point script can find the modules
        self.runenv_info.define("PYTHONPATH", self.package_folder)
