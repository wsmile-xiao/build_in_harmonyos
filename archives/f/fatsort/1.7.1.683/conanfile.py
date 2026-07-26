#!/usr/bin/env python3
"""Conan recipe for fatsort 1.7.1.683 — Makefile-based terminal tool."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get, export_conandata_patches
from conan.tools.layout import basic_layout


class FatsortConan(ConanFile):
    name = "fatsort"
    version = "1.7.1.683"
    description = "FATSort sorts directory structures of FAT/exFAT file systems"
    license = "GPL-2.0-or-later"
    homepage = "https://fatsort.sourceforge.io/"
    url = "https://sourceforge.net/projects/fatsort/"
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"])

    def build(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("fatsort supports Linux/OHOS-style POSIX platforms")
        apply_conandata_patches(self)
        src_dir = os.path.join(self.source_folder, "src")
        self.run(f"make -C {src_dir} -j1 CC=clang LD=clang CFLAGS=\"-fPIC -O2 -D__LINUX__\"", env="conanbuild")

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "fatsort", os.path.join(self.source_folder, "src"), os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "fatsort.1", os.path.join(self.source_folder, "man"), os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
