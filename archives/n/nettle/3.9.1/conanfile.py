#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Nettle, nettle, 3.9.1, Low-level cryptographic library (AES, DES, RSA, SHA, etc.), LGPL-2.1-or-later, https://ftp.gnu.org/gnu/nettle/
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NettleConan(ConanFile):
    name = "nettle"
    version = "3.9.1"
    description = "Low-level cryptographic library (AES, DES, RSA, SHA, etc.)"
    license = "LGPL-2.1-or-later"
    homepage = "https://ftp.gnu.org/gnu/nettle/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # E001: HarmonyOS PATH has no `cc` symlink; force clang explicitly
        tc.update_configure_args({"CC": "clang", "CXX": "clang++"})
        # R49: pass gmp dependency include/lib paths via build-private prefix so
        # configure can enable public-key crypto (hogweed); never inject shared
        # system prefix like /usr/local.
        gmp = self.dependencies["gmp"]
        tc.configure_args.append(f"--with-include-path={gmp.cpp_info.includedirs[0]}")
        tc.configure_args.append(f"--with-lib-path={gmp.cpp_info.libdirs[0]}")
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
        self.cpp_info.libs = ["nettle"]
