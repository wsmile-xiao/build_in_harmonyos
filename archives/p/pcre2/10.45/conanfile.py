#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Pcre2, pcre2, 10.45, Perl Compatible Regular Expressions library (version 2, current), BSD-3-Clause, https://www.pcre.org/
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Pcre2Conan(ConanFile):
    name = "pcre2"
    version = "10.45"
    description = "Perl Compatible Regular Expressions library (version 2, current)"
    license = "BSD-3-Clause"
    homepage = "https://www.pcre.org/"
    url = ""  # CI fills this

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
        # R26: Terminal tools must be statically linked
        # Explicitly set build triplet for HarmonyOS (config.guess may fail in conan sandbox)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
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
        self.cpp_info.libs = ["pcre2-8", "pcre2-posix"]
