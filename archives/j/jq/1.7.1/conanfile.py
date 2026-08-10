#!/usr/bin/env python3
"""Conan recipe — jq 1.7.1 (command-line JSON processor)

jq bundles oniguruma internally; --with-oniguruma=builtin enables full
regex support without external dependencies.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JqConan(ConanFile):
    name = "jq"
    version = "1.7.1"
    description = "Command-line JSON processor"
    license = "MIT / CC-BY-3.0"
    homepage = "https://jqlang.github.io/jq/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        tc.configure_args.append("--with-oniguruma=builtin")
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
        self.cpp_info.libs = ["jq"]
        self.cpp_info.bindirs = ["bin"]
