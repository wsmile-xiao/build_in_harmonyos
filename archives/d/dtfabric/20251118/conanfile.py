#!/usr/bin/env python3
"""Conan recipe for dtfabric 20251118 — Pure Python setuptools package.

dtfabric is a tool for data type and structure management, using YAML-based
data type definitions. Pure Python, no C/C++ compilation required.
python_requires >=3.10.
"""

import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DtFabricConan(ConanFile):
    name = "dtfabric"
    version = "20251118"
    description = "Tooling for data type and structure management"
    license = "Apache-2.0"
    homepage = "https://github.com/libyal/dtfabric"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        pass

    def requirements(self):
        # PyYAML is a pip dependency installed via pip in build(); not a Conan recipe.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Python setuptools: ensure build deps then pip install --target
        staging = os.path.join(self.build_folder, "staging")
        self.run(f"{sys.executable} -m pip install setuptools wheel --quiet",
                 cwd=self.source_folder)
        self.run(f"{sys.executable} -m pip install . "
                 f"--target={staging} "
                 f"--no-build-isolation "
                 f"--no-deps",
                 cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        copy(self, "*", src=staging, dst=os.path.join(self.package_folder))
        # Copy license
        for lic_name in ("LICENSE", "LICENSE.txt", "LICENCE"):
            src = os.path.join(self.source_folder, lic_name)
            if os.path.isfile(src):
                copy(self, lic_name, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"))
                break

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
