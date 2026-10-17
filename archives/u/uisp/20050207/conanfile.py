#!/usr/bin/env python3
"""Conan recipe — uisp (Micro In-System Programmer for Atmel AVR MCUs).

Autotools CLI tool. Adapted for OHOS (clang 15): C++11 narrowing and
string-literal fixes are carried as patches generated from the
exploration build (see notes.md).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UispConan(ConanFile):
    name = "uisp"
    version = "20050207"
    description = "Micro In-System Programmer (uisp) for Atmel AVR microcontrollers"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/uisp/"
    url = ""  # CI fills this

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
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
