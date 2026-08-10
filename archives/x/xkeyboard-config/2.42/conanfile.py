#!/usr/bin/env python3
"""Conan recipe — xkeyboard-config 2.42 (XKB keyboard configuration data, Meson).

Data-only package: no libraries, no executables, no headers.
Installs XKB configuration data (rules, symbols, keycodes, compat, geometry,
types) + a dataonly pkg-config file (xkeyboard-config.pc) + man page.

Build system: Meson + Ninja.
Requires: xsltproc (from libxslt, available on OHOS build host via HNP).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class XkeyboardConfigConan(ConanFile):
    name = "xkeyboard-config"
    version = "2.42"
    description = "X Keyboard configuration data (XKB rules, symbols, keycodes)"
    license = "MIT"
    homepage = "https://www.x.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
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
        # Data-only package: expose the dataonly pkg-config file for consumers.
        self.cpp_info.set_property("pkg_config_name", "xkeyboard-config")
        # No libraries / headers / binaries to declare.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
