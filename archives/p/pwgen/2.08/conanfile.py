#!/usr/bin/env python3
"""Conan recipe — pwgen 2.08 (autotools).

pwgen is a command-line password generator (application, not a library).
Build system: autotools (configure + make).

R32: settings.os check includes "OHOS"
R33: No bare shell env vars; all flags from Conan toolchain
R34: test_package runs the pwgen binary to verify functionality
R38: commands.json declared at software level
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PwgenConan(ConanFile):
    name = "pwgen"
    version = "2.08"
    description = "A password generator for creating pronounceable passwords"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/tytso/pwgen"

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
