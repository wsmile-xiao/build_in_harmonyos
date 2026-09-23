#!/usr/bin/env python3
"""Conan recipe — ondir 0.2.3 (hand-written Makefile, no autoconf)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OndirConan(ConanFile):
    name = "ondir"
    version = "0.2.3"
    description = "Run directory-specific scripts when entering or leaving a directory"
    license = "BSD-3-Clause"
    homepage = "https://github.com/alecthomas/ondir"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # The official codeload URL ends with the bare commit sha, so Conan
        # cannot infer the archive format from the basename -> pass an
        # explicit filename so it is unpacked as tar.gz (not zip).
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="ondir-0.2.3.tar.gz")

    def build(self):
        apply_conandata_patches(self)
        # Legacy single-shot Makefile -> keep -j1 (R9).
        # The OHOS toolchain has no `cc`; patches/0001 points CC/LD at clang.
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Command-line tool -> the binary is the payload (R38).
        copy(self, "ondir", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # Man page.
        copy(self, "ondir.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share/man/man1"))
        # Shell integration hooks (bash/tcsh/zsh) + example ondirrc.
        copy(self, "scripts.*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share/ondir"))
        copy(self, "ondirrc.eg", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share/ondir"))
        # Upstream documentation.
        copy(self, "README.rst", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share/doc/ondir"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share/doc/ondir"))
        copy(self, "ChangeLog", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share/doc/ondir"))
        copy(self, "AUTHORS", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share/doc/ondir"))
        copy(self, "INSTALL", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share/doc/ondir"))

    def package_info(self):
        # Standalone CLI tool: no library is exported.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
