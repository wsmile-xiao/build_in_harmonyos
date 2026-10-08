#!/usr/bin/env python3
"""Conan recipe — sysnews 0.9-ds.1 (plain Makefile, C).

sysnews provides the `news` command: display system news articles kept in
a directory (default /var/sysnews), with expire support.
Build system: plain Makefile (no configure); `make install` needs root
(`install -o bin -g bin`), so package() copies the outputs instead.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SysnewsConan(ConanFile):
    name = "sysnews"
    version = "0.9-ds.1"
    description = "Display system news articles at login (news command)"
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/sysnews"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sysnews supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang") if comp else "clang"
        self.run(f"make -j1 CC='{cc}' CFLAGS='-Wall -O2'", cwd=self.source_folder)

    def package(self):
        copy(self, "news", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "news.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
