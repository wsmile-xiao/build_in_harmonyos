#!/usr/bin/env python3
"""Conan recipe — darkhttpd 1.17 (makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DarkhttpdConan(ConanFile):
    name = "darkhttpd"
    version = "1.17"
    description = "A small, single-file, zero-dependency HTTP server"
    license = "ISC"
    homepage = "https://github.com/emikulic/darkhttpd"

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
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        self.run(f"make -C {self.source_folder} CC={cc} -j1")

    def package(self):
        copy(self, "darkhttpd", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
