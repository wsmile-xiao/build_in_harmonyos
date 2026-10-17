#!/usr/bin/env python3
"""Conan recipe for buckygen 1.1 — efficient generation of nonisomorphic fullerenes.

Buckygen is a command-line program for generating all nonisomorphic fullerenes
(triangulations where all vertices have degree 5 or 6, i.e. cubic plane graphs
whose faces are pentagons or hexagons).  It can also generate IPR fullerenes.

Build system: plain Makefile (no configure, no autotools, no cmake).
License: GPL-3.0.
No external library dependencies — only the standard C library.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class BuckygenConan(ConanFile):
    name = "buckygen"
    version = "1.1"
    description = "Efficient generation of nonisomorphic fullerenes"
    license = "GPL-3.0"
    homepage = "http://caagt.ugent.be/buckygen/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # R9: Always use -j1
        self.run(f"make -j1 CC={cc}")

    def package(self):
        # The Makefile has no install target — copy the binary manually.
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "buckygen"),
            os.path.join(bin_dir, "buckygen"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
