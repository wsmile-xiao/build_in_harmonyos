#!/usr/bin/env python3
"""Conan recipe for bstring 1.0.3 — Meson build system.

bstring is a fork of Paul Hsieh's Better String Library, focusing on
safety and usability for C string handling. Builds a shared library
(libbstring.so) with meson.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class BstringConan(ConanFile):
    name = "bstring"
    version = "1.0.3"
    description = "Fork of Paul Hsieh's Better String Library for C"
    license = "BSD-3-Clause"
    homepage = "https://github.com/msteinert/bstring"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared"
        tc.generate()
        # Add ar to meson native file (profile doesn't set tools.build:archiver)
        native_file = self.generators_folder + "/conan_meson_native.ini"
        with open(native_file) as f:
            content = f.read()
        old_content = content
        content = content.replace(
            "[binaries]\nc =",
            "[binaries]\nar = '/data/service/hnp/bin/ar'\nc ="
        )
        if content == old_content:
            raise RuntimeError("Failed to inject ar into meson native file "
                               "(pattern '[binaries]\\nc =' not found)")
        with open(native_file, "w") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["bstring"]
