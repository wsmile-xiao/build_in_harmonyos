#!/usr/bin/env python3
"""Conan recipe for the pure-Python vincenty 0.1.4 library."""

import os
import sys

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class VincentyConan(ConanFile):
    name = "vincenty"
    version = "0.1.4"
    description = "Calculate precise geodesic distances with Vincenty's formula"
    license = "Unlicense"
    homepage = "https://github.com/maurycyp/vincenty"
    url = "https://github.com/maurycyp/vincenty"

    # Conan's "library" type requires a C/C++ shared option. This source-only
    # Python package deliberately uses the neutral type.
    package_type = "unknown"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        test_env = Environment()
        test_env.prepend_path("PYTHONPATH", self.source_folder)
        with test_env.vars(self).apply():
            self.run(
                f'"{sys.executable}" -m doctest -v '
                f'"{os.path.join(self.source_folder, "vincenty", "__init__.py")}"',
                cwd=self.source_folder,
            )

    def package(self):
        module_src = os.path.join(self.source_folder, "vincenty")
        module_dst = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
            "vincenty",
        )
        copy(self, "__init__.py", src=module_src, dst=module_dst, keep_path=False)
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
