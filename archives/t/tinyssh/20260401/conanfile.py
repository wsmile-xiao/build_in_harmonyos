"""Conan recipe for tinyssh — a small SSH server using modern cryptography.

tinyssh builds with a plain Makefile (no configure script). The Makefile
generates auto-headers via tryfeature.sh which probes system capabilities.
Build products are executables installed to sbin/.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TinysshConan(ConanFile):
    name = "tinyssh"
    version = "20260401"
    description = "Small SSH server using modern cryptography (Ed25519, Curve25519, Chacha20-Poly1305)"
    license = "CC0-1.0"
    homepage = "https://github.com/janmojzis/tinyssh"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c", "clang")

        # tinyssh Makefile uses CC?=cc; we override with the conan compiler.
        # tryfeature.sh requires CC to be set in the environment.
        # R9: Always use -j1
        self.run(f'make CC="{cc}" -j1', cwd=self.source_folder)

    def package(self):
        # Install using the Makefile's install target.
        # PREFIX= (empty) means install goes directly to DESTDIR/sbin/
        self.run(f"make install DESTDIR={self.package_folder} PREFIX=", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["sbin"]
