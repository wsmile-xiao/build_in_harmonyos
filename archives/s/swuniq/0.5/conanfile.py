#!/usr/bin/env python3
"""Conan recipe — swuniq 0.5 (single-file C CLI)."""
from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os
import shlex


class SwuniqConan(ConanFile):
    name = "swuniq"
    version = "0.5"
    description = "Sliding-window line deduplication command"
    license = "MIT"
    homepage = "https://github.com/mterron/swuniq"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "cc")
        cflags = self.conf.get("tools.build:cflags", default=[])
        flags = ["-O2", *cflags, "-static"]
        args = [cc, *flags, "swuniq.c", "-o", os.path.join(self.build_folder, "swuniq")]
        self.run(" ".join(shlex.quote(str(arg)) for arg in args), cwd=self.source_folder)

    def package(self):
        copy(self, "swuniq", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
