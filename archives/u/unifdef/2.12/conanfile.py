#!/usr/bin/env python3
"""Conan recipe for unifdef 2.12.

unifdef uses a custom Makefile (not autotools configure).
It is a terminal tool (binary), so package_info uses bindirs.
R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment


class UnifdefConan(ConanFile):
    name = "unifdef"
    version = "2.12"
    description = "Selectively process conditional C preprocessor directives"
    license = "BSD-2-Clause AND BSD-3-Clause"
    homepage = "http://dotat.at/prog/unifdef"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Terminal tools must be statically linked
        env = Environment()
        env.define("BUILD_SHARED_LIBS", "OFF")
        env.vars(self).save_script("unifdef_env")

    def build(self):
        apply_conandata_patches(self)
        # unifdef uses a custom Makefile, not autotools configure
        self.run("make -j1")

    def package(self):
        # Install using make install with DESTDIR
        self.run(f"make install DESTDIR={self.package_folder} prefix=/")

    def package_info(self):
        # Terminal tool: use bindirs, not libs
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
