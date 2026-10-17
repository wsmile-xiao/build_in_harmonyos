#!/usr/bin/env python3
"""Conan recipe for cmph 2.0 — C Minimal Perfect Hashing Library.

Autotools project. Requires OHOS platform patches for config.guess/config.sub,
umask fix for HMDFS filesystem, and printf fix for bash compatibility.
Uses in-tree build due to old Makefile.in lacking proper $(srcdir) support.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CmphConan(ConanFile):
    name = "cmph"
    version = "2.0"
    description = "C Minimal Perfect Hashing Library"
    license = "LGPL-2.1"
    homepage = "https://cmph.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        # In-tree build: old Makefile.in lacks proper $(srcdir) for out-of-tree
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
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
        self.cpp_info.libs = ["cmph"]
