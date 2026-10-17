#!/usr/bin/env python3
"""Conan recipe for faac 1.40 — Freeware Advanced Audio Coder.

faac is an AAC audio encoder library and command-line tool.
Build system: Meson.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class FaacConan(ConanFile):
    name = "faac"
    version = "1.40"
    description = "Freeware Advanced Audio Coder — AAC encoder library and CLI tool"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/knik0/faac"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "frontend": [True, False],
    }
    default_options = {
        "shared": False,
        "frontend": True,
    }

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
        tc.project_options["frontend"] = "true" if self.options.frontend else "false"
        # HarmonyOS: posix_spawn does not search PATH, so set full paths for tools
        if not tc.ar:
            tc.ar = "/data/service/hnp/bin/llvm-ar"
        if not tc.strip:
            tc.strip = "/data/service/hnp/bin/llvm-strip"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["faac"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        if self.options.frontend:
            self.cpp_info.bindirs = ["bin"]
