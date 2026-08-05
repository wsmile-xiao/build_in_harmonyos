#!/usr/bin/env python3
"""
Conan recipe for chmlib v0.40 — OHOS (OpenHarmony) aarch64 adaptation.

Build system: autotools (configure + make).
Source tarball from Slackware mirror (original jedrea.com release, offline).
4 portability patches verified on OHOS aarch64 (2026-06-03).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ChmlibConan(ConanFile):
    name = "chmlib"
    version = "0.40"
    description = "Library for reading Microsoft ITSS/CHM format files"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/jedwing/CHMLib"
    url = "https://github.com/jedwing/CHMLib"

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
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        tc.configure_args.append("--enable-examples=no")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["chm"]
