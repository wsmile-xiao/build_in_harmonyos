#!/usr/bin/env python3
"""Conan recipe — ttyrec 1.0.8 (Makefile)"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TtyrecConan(ConanFile):
    name = "ttyrec"
    version = "1.0.8"
    description = "Terminal interaction recorder and player"
    license = "BSD-4-Clause"
    homepage = "http://0xcc.net/ttyrec/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        cc_executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_executables.get("c", "clang")
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "ttyrec", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "ttyplay", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "ttytime", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "*.1", self.source_folder, os.path.join(self.package_folder, "share/man/man1"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
