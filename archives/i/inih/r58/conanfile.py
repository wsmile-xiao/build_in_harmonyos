#!/usr/bin/env python3
"""Conan recipe for inih r58 — Meson build system.

inih (INI Not Invented Here) is a simple INI file parser written in C.
It's only a couple of pages of code, designed to be small and simple
for embedded systems. Compatible with Python's ConfigParser-style INI files.

Build: Meson with default_library=static (small embedded-style library).
No external dependencies — pure C standard library only.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class InihConan(ConanFile):
    name = "inih"
    version = "r58"
    description = "Simple INI file parser in C, good for embedded systems"
    license = "BSD-3-Clause"
    homepage = "https://github.com/benhoyt/inih"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # inih has zero external dependencies — pure C standard library
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # Build static library for this small embedded-style library
        tc.project_options["default_library"] = "static"
        # Disable C++ INIReader (not needed for C consumers)
        tc.project_options["with_INIReader"] = "false"
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
        # Meson pkg-config name is "inih"; library file is libinih.a
        self.cpp_info.libs = ["inih"]
