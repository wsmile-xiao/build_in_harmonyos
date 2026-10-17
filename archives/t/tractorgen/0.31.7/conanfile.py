#!/usr/bin/env python3
"""Conan recipe — tractorgen 0.31.7

A small C CLI tool (Autotools) that generates ASCII tractors.
No third-party runtime dependencies.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TractorgenConan(ConanFile):
    name = "tractorgen"
    version = "0.31.7"
    description = "An ASCII tractor generator"
    license = "GPL-2.0-or-later"
    homepage = "https://vergenet.net/~conrad/software/tractorgen/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # R15: No --build/--host — tractorgen's configure (autoconf 2.13) does not
        # reference config.guess/config.sub files that could cause OHOS detection issues
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
        # tractorgen is a terminal tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
