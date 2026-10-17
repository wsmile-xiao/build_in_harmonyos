#!/usr/bin/env python3
"""Conan recipe for termpaint 0.3.0 — Meson build system.

termpaint is a low-level terminal interface library for modern terminals.
License: BSL-1.0 (Boost Software License)
Homepage: https://github.com/termpaint/termpaint
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class TermpaintConan(ConanFile):
    name = "termpaint"
    version = "0.3.0"
    description = "Low level terminal interface library for modern terminals"
    license = "BSL-1.0"
    homepage = "https://github.com/termpaint/termpaint"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["ttyrescue-fexec-blob"] = "false"
        if tc.c:
            cc_dir = os.path.dirname(tc.c)
            ar_path = os.path.join(cc_dir, "llvm-ar")
            if os.path.isfile(ar_path):
                tc.binaries["ar"] = ar_path
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build(target="termpaint")
        meson.build(target="termpaint_image")

    def package(self):
        # Use --no-rebuild to skip full ninja build (testtermpaint link fails in C++17)
        meson = Meson(self)
        meson.install(cli_args=["--no-rebuild"])

    def package_info(self):
        self.cpp_info.libs = ["termpaint"]
        # termpaint links against librt for clock_gettime
        self.cpp_info.system_libs = ["rt"]
