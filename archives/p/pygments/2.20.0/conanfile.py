#!/usr/bin/env python3
"""Conan recipe for packaging the pure-Python Pygments 2.20.0 library."""

import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PygmentsConan(ConanFile):
    name = "pygments"
    version = "2.20.0"
    description = "Pygments is a syntax highlighting package written in Python."
    license = "BSD-2-Clause"
    homepage = "https://pygments.org/"
    url = "https://github.com/pygments/pygments"

    package_type = "unknown"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def validate(self):
        if sys.version_info < (3, 9):
            raise ConanInvalidConfiguration("Pygments 2.20.0 requires Python 3.9 or newer")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Run the upstream core API test files (avoid the full golden-master
        # lexer matrix which is slow and only checks generated samples).
        test_files = [
            "tests/test_basic_api.py",
            "tests/test_cmdline.py",
            "tests/test_using_api.py",
            "tests/test_token.py",
        ]
        build_env = Environment()
        build_env.prepend_path("PYTHONPATH", self.source_folder)
        with build_env.vars(self).apply():
            self.run(
                f'"{sys.executable}" -m pytest -q {" ".join(test_files)}',
                cwd=self.source_folder,
            )

    def package(self):
        site_packages = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "pygments"),
            dst=os.path.join(site_packages, "pygments"),
            keep_path=True,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        site_packages = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
        )
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
