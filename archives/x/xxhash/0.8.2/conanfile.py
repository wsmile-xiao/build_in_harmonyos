#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Xxhash, xxhash, 0.8.2, Extremely fast non-cryptographic hash algorithm library (XXH32, XXH64, XXH3, XXH128), BSD-2-Clause, https://github.com/Cyan4973/xxHash
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XxhashConan(ConanFile):
    name = "xxhash"
    version = "0.8.2"
    description = "Extremely fast non-cryptographic hash algorithm library (XXH32, XXH64, XXH3, XXH128)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/Cyan4973/xxHash"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        # xxHash uses pure Makefile without configure
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # xxHash has no configure step, build directly with make
        # Build in source folder where Makefile is located
        if self.options.shared:
            autotools.make(target="lib", args=["-j1", f"-C {self.source_folder}"])
        else:
            # Build static library only
            autotools.make(target="libxxhash.a", args=["-j1", f"-C {self.source_folder}"])

    def package(self):
        autotools = Autotools(self)
        # Use DESTDIR for staging, PREFIX should be empty or /
        if self.options.shared:
            autotools.install(args=["PREFIX=/", f"-C {self.source_folder}"])
        else:
            # For static library, only install static lib, headers and pkg-config
            autotools.install(target="install_libxxhash.a", args=["PREFIX=/", f"-C {self.source_folder}"])
            autotools.install(target="install_libxxhash.includes", args=["PREFIX=/", f"-C {self.source_folder}"])
            autotools.install(target="install_libxxhash.pc", args=["PREFIX=/", f"-C {self.source_folder}"])

    def package_info(self):
        self.cpp_info.libs = ["xxhash"]
