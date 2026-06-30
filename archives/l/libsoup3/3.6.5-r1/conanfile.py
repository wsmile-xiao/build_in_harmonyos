#!/usr/bin/env python3
"""Conan recipe template — Meson projects.

Usage: Replace Libsoup3, libsoup3, 3.6.5-r1, libsoup3 3.6.5-r1, MIT, 
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: default_library=static for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain, meson_layout


class Libsoup3Conan(ConanFile):
    name = "libsoup3"
    version = "3.6.5-r1"
    description = "libsoup3 3.6.5-r1"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        meson_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.project_options["default_library"] = "static"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.compile()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["libsoup3"]
