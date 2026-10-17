#!/usr/bin/env python3
"""Conan recipe for libbcrypt (crypt_blowfish) 1.3.

Blowfish-based password hashing library from OpenWall.
Source: crypt_blowfish-1.3.tar.gz (contains crypt_blowfish.c, wrapper.c, etc.)

Key adaptation notes:
  - x86.S is x86-only assembly; on aarch64 BF_ASM=0 (C implementation used)
  - Upstream Makefile has no library target; we create libbcrypt.a with ar
  - No configure script; raw make
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibbcryptConan(ConanFile):
    name = "libbcrypt"
    version = "1.3"
    description = "Blowfish-based password hashing library"
    license = "Public-Domain"
    homepage = "https://www.openwall.com/crypt/"
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

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        ar = comp_execs.get("ar") or "llvm-ar"
        ranlib = comp_execs.get("ranlib") or "llvm-ranlib"

        # Build object files without x86.o (x86 assembly, not applicable on aarch64
        # where BF_ASM=0 — the C implementation in crypt_blowfish.c is used).
        # Respect build_type: Debug → -O0 -g, Release → -O2 (review fix).
        if self.settings.build_type == "Debug":
            cflags = "-W -Wall -O0 -g -fPIC"
        else:
            cflags = "-W -Wall -O2 -fPIC"
        # R9: Always use -j1.
        self.run(f'make CC="{cc}" BLOWFISH_OBJS="crypt_blowfish.o" '
                 f'CFLAGS="{cflags}" -j1',
                 cwd=self.source_folder)

        # Upstream Makefile has no library target; create static library manually.
        self.run(f'{ar} rcs libbcrypt.a crypt_blowfish.o crypt_gensalt.o wrapper.o',
                 cwd=self.source_folder)
        if ranlib:
            self.run(f'{ranlib} libbcrypt.a', cwd=self.source_folder)

    def package(self):
        # Install headers
        copy(self, "ow-crypt.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "crypt_blowfish.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "crypt_gensalt.h", self.source_folder, os.path.join(self.package_folder, "include"))
        # Install library
        copy(self, "libbcrypt.a", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["bcrypt"]
