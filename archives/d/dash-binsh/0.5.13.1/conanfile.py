#!/usr/bin/env python3
"""Conan recipe — dash-binsh 0.5.13.1 (Debian Almquist Shell).

POSIX-compliant shell optimized for size and speed. Produces the `dash` executable.
Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos) with OHOS-aware
config.guess/config.sub and HMDFS-safe mkbuiltins pipe handling.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DashBinshConan(ConanFile):
    name = "dash-binsh"
    version = "0.5.13.1"
    description = "Debian Almquist Shell — POSIX-compliant shell optimized for size and speed"
    license = "BSD-3-Clause"
    homepage = "http://gondor.apana.org.au/~herbert/dash/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git"

    package_type = "application"

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
        self.cpp_info.bindirs = ["bin"]