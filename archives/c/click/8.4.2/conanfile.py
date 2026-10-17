#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for click 8.4.2"""

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
import os
import sys


class ClickConan(ConanFile):
    name = "click"
    version = "8.4.2"
    license = "BSD-3-Clause"
    author = "Pallets"
    url = "https://github.com/pallets/click"
    homepage = "https://click.palletsprojects.com/"
    description = "Composable command line interface toolkit"
    topics = ("cli", "python", "terminal")
    package_type = "application"
    settings = "os", "arch"

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Build the package using pip
        # Install directly to a target directory (with all dependencies)
        install_target = os.path.join(self.build_folder, "install")
        self.run(
            f'{sys.executable} -m pip install --no-deps --target="{install_target}" "{self.source_folder}"'
        )

    def package(self):
        # Copy the installed files from build folder to package folder
        install_target = os.path.join(self.build_folder, "install")
        copy(self, "*", dst=self.package_folder, src=install_target)

    def package_info(self):
        # Python package information
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

        # Python-specific environment
        # Use the package folder directly (pip --target is flat installation)
        python_path = self.package_folder

        self.output.info(f"Setting PYTHONPATH: {python_path}")
        self.runenv_info.prepend_path("PYTHONPATH", python_path)