#!/usr/bin/env python3
"""Conan recipe — httptunnel 3.3 (command-line tools hts/htc).

httptunnel creates a bidirectional virtual data connection tunneled in
HTTP requests. hts is the server side, htc the client side.
Build system: autotools (configure + make). No external dependencies.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class HttptunnelConan(ConanFile):
    name = "httptunnel"
    version = "3.3"
    description = "hts/htc: creates a bidirectional virtual data connection tunneled in HTTP requests"
    license = "GPL-2.0-or-later"
    homepage = "https://ftp.gnu.org/gnu/httptunnel/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"httptunnel is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
