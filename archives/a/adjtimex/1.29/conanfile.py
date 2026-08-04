#!/usr/bin/env python3
"""Conan recipe for adjtimex 1.29.

adjtimex - display or set the kernel time variables.
Build system: Autotools (configure + make).
Pure C, no third-party Conan dependencies (only musl libc).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AdjtimexConan(ConanFile):
    name = "adjtimex"
    version = "1.29"
    description = "adjtimex - display or set the kernel time variables"
    license = "GPL-2.0-or-later"
    homepage = "http://linux.die.net/man/8/adjtimex"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # adjtimex Makefile requires Makefile.in in the build dir (in-source
        # build only); out-of-source fails with "No rule to make target
        # 'Makefile.in'". Same approach as the at recipe.
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

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
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
