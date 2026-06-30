#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Libntlm, libntlm, 1.8, NTLM authentication library, LGPL-2.1, https://www.nongnu.org/libntlm/
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibntlmConan(ConanFile):
    name = "libntlm"
    version = "1.8"
    description = "NTLM authentication library"
    license = "LGPL-2.1"
    homepage = "https://www.nongnu.org/libntlm/"
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
        # R26: Static linking — build only static libraries
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        tc.extra_ldflags.append("-static")
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
        self.cpp_info.libs = ["ntlm"]
