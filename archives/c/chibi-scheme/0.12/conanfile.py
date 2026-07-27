#!/usr/bin/env python3
"""Conan recipe for chibi-scheme 0.12.

chibi-scheme is a small footprint Scheme implementation designed as a
C extension language. It uses a custom Makefile build system.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ChibiSchemeConan(ConanFile):
    name = "chibi-scheme"
    version = "0.12"
    description = "Small footprint Scheme for use as a C Extension Language"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ashinn/chibi-scheme"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        self.run(f"make -C {self.source_folder} CC={cc} PLATFORM=unix -j1")

    def package(self):
        self.run(f"make -C {self.source_folder} install PREFIX=/ DESTDIR={self.package_folder} PLATFORM=unix")

    def package_info(self):
        self.cpp_info.libs = ["chibi-scheme"]
