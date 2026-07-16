#!/usr/bin/env python3
"""Conan recipe for dateutils 0.4.11-r0 — date utility programs.

dateutils provides a set of command-line tools for working with dates and times,
including dateadd, datediff, dategrep, dateround, dateseq, datesort, etc.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DateutilsConan(ConanFile):
    name = "dateutils"
    version = "0.4.11-r0"
    description = "nifty command line date and time utilities"
    license = "MIT"
    homepage = "https://github.com/hroptatyr/dateutils"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("CC=clang")
        tc.configure_args.append("CXX=clang++")
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
        self.cpp_info.bindirs = ["bin"]
