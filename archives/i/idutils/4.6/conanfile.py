#!/usr/bin/env python3
"""Conan recipe — idutils 4.6 (Autotools)"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IdutilsConan(ConanFile):
    name = "idutils"
    version = "4.6"
    description = "ID database and query tools — create and maintain identifier databases"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/idutils/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R33: CPP must be set via toolchain, not shell env
        # autoconf may add -traditional-cpp which fails sanity check on OHOS
        if self.settings.os in ("Linux", "OHOS"):
            tc.configure_args.append("CPP=clang -E")
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
