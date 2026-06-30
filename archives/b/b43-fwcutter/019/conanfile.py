#!/usr/bin/env python3
"""Conan recipe — b43-fwcutter 019 (simple Makefile, not autotools).

Build system: Plain Makefile (no configure script).
b43-fwcutter extracts firmware from Broadcom 43xx driver files.

R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class B43FwcutterConan(ConanFile):
    name = "b43-fwcutter"
    version = "019"
    description = "Extract firmware from Broadcom 43xx driver files"
    license = "MIT"
    homepage = "https://bues.ch/b43/fwcutter/"
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
        # R26: Terminal tools must be statically linked
        # BUILD_SHARED_LIBS=OFF ensures no shared libraries are built
        from conan.tools.env import Environment
        env = Environment()
        env.define("BUILD_SHARED_LIBS", "OFF")
        env.define("CC", "clang")
        env.define("LDFLAGS", "-static")
        envvars = env.vars(self)
        envvars.save_script("b43_fwcutter_env")

    def build(self):
        # Apply patches from conandata.yml (0001-Makefile.patch:
        # removes root ownership, adds DESTDIR support)
        apply_conandata_patches(self)
        src = self.source_folder
        # Build with clang and static linking (run in source dir where Makefile lives)
        self.run(
            "make CC=clang CFLAGS='-fPIC -O2 -std=c99 -Wall -pedantic -D_BSD_SOURCE -DFWCUTTER_VERSION_=019' LDFLAGS='-static' -j1",
            cwd=src
        )

    def package(self):
        src = self.source_folder
        # Install to package directory using DESTDIR with empty PREFIX
        # so binaries go to {package_folder}/bin/ (Conan standard layout)
        self.run(
            f"make install DESTDIR={self.package_folder} PREFIX= CC=clang",
            cwd=src
        )

    def package_info(self):
        self.cpp_info.libs = ["b43-fwcutter"]
        self.cpp_info.bindirs = ["bin"]
