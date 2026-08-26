#!/usr/bin/env python3
"""Conan recipe for libdshconfig 0.20.13 — Autotools projects (configure + make).

Patches in conandata.yml handle:
  - config.guess/config.sub update for OHOS platform recognition
  - umask 077→022 fix for HMDFS compatibility
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibdshconfigConan(ConanFile):
    name = "libdshconfig"
    version = "0.20.13"
    description = "A library to read dsh config file style data files"
    license = "GPL-2.0-or-later"
    homepage = "https://www.netfort.gr.jp/~dancer/software/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["dshconfig"]
