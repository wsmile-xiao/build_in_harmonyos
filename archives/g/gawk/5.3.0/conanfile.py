#!/usr/bin/env python3
"""Conan recipe for gawk 5.3.0 — GNU Awk text processing language.

Build system: Autotools (configure + make).
gawk is a command-line tool (application), not a library.

OHOS adaptation:
  - config.guess/config.sub: HarmonyOS platform detection
  - fstat() EACCES handling for pipes/terminals/sockets
  - _BSD_SOURCE → _GNU_SOURCE in extensions
  - pma.h include path fix
  - HMDFS umask 077 fix via patches (configure and extension/configure)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GawkConan(ConanFile):
    name = "gawk"
    version = "5.3.0"
    description = "GNU implementation of the AWK text processing language"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gawk/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

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
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
