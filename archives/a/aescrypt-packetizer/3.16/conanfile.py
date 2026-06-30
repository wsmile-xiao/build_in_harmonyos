#!/usr/bin/env python3
"""Conan recipe for aescrypt-packetizer 3.16 — plain Makefile project.

AES Crypt is a command-line file encryption tool using AES-256.
This project uses a plain Makefile (not autotools/cmake), so the recipe
uses direct make invocation with environment overrides.

R26: Terminal tools must be statically linked (LDFLAGS=-static).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class AescryptpacketizerConan(ConanFile):
    name = "aescrypt-packetizer"
    version = "3.16"
    description = "AES Crypt - command-line file encryption tool using AES-256"
    license = "GPL-2.0-or-later"
    homepage = "https://www.aescrypt.com/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Terminal tools must be statically linked (-static in LDFLAGS)
        # LDFLAGS=-static is passed directly in build() make command line
        pass

    def build(self):
        apply_conandata_patches(self)
        src_dir = os.path.join(self.source_folder, "src")
        # Plain Makefile project — override CC, CFLAGS, LDLIBS on command line
        # HarmonyOS uname returns "HarmonyOS" not "Linux", so Makefile
        # incorrectly adds -liconv; override LDLIBS= to fix.
        # R26: LDFLAGS=-static for static linking of terminal tools
        self.run(
            f'make -C "{src_dir}" '
            'CC=clang '
            'CFLAGS="-fPIC -O2 -Wall -Wextra -pedantic -std=c11 -D_FILE_OFFSET_BITS=64" '
            'LDLIBS= '
            'LDFLAGS=-static',
            env="conanbuild"
        )

    def package(self):
        # Manual install — Makefile doesn't support DESTDIR
        copy(self, "aescrypt",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "aescrypt_keygen",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "aescrypt.1",
             src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "aescrypt_keygen.1",
             src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # Terminal tool — no library to link against
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
