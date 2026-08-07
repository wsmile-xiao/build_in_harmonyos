#!/usr/bin/env python3
"""Conan recipe for lzip 1.25 — LZMA lossless data compressor.

lzip is a command-line compression tool (not a library).
It uses a custom configure script (not GNU autoconf).
E095: lzip's configure doesn't read $CXX env var; requires CXX= as arg.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LzipConan(ConanFile):
    name = "lzip"
    version = "1.25"
    description = "LZMA lossless data compressor"
    license = "GPL-2.0+"
    homepage = "https://www.nongnu.org/lzip/"
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
        # E095: lzip's custom configure script (not autoconf) doesn't
        # read $CXX env var; requires CXX=<compiler> as command-line arg.
        # R33: get compiler from Conan conf, not shell env.
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cxx = compilers.get("cpp", "clang++")
        tc.configure_args.append(f"CXX={cxx}")
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
