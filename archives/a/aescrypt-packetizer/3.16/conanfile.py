#!/usr/bin/env python3
"""Conan recipe for aescrypt-packetizer 3.16 — AES Crypt packetizer library.

Build system: raw Makefile (C project).  We build a static library from the
core source files (aes, sha256, password, keyfile, util), excluding the
aescrypt / aescrypt_keygen command-line entry points.

Core API:
  - aes_context / aes_set_key / aes_encrypt / aes_decrypt  (AES-256)
  - sha256_context / sha256_starts / sha256_update / sha256_finish  (SHA-256)
  - password / keyfile / util helpers

License: GPL-2.0 (aes.c/h, sha256.c/h) + freeware (remaining files)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AescryptpacketizerConan(ConanFile):
    name = "aescrypt-packetizer"
    version = "3.16"
    description = "AES Crypt packetizer library — AES-256 encryption / SHA-256 hashing / password & keyfile utilities"
    license = "GPL-2.0-or-later"
    homepage = "https://www.aescrypt.com"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False]}
    default_options = {"shared": False}

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

        # R33: Get compiler from environment, never from shell ${CC} in self.run().
        cc = os.environ.get("CC", "clang")
        ar = os.environ.get("AR", "llvm-ar")
        ranlib = os.environ.get("RANLIB", "llvm-ranlib")

        src_dir = os.path.join(self.source_folder, "src")
        build_dir = self.build_folder

        # Core library sources (excluding CLI entry-points aescrypt.c, aescrypt_keygen.c)
        lib_srcs = [
            "aes.c",
            "sha256.c",
            "password.c",
            "keyfile.c",
            "util.c",
        ]

        # R9: Always use -j1
        cflags = "-O3 -Wall -Wextra -pedantic -std=c11 -D_FILE_OFFSET_BITS=64 -fPIC"

        objs = []
        for src in lib_srcs:
            obj = src.replace(".c", ".o")
            self.run(f"{cc} {cflags} -I{src_dir} -c {src_dir}/{src} -o {build_dir}/{obj}")
            objs.append(obj)

        # Archive into static library
        lib_name = "libAESCryptPacketizer.a"
        lib_path = os.path.join(build_dir, lib_name)
        self.run(f"{ar} rcs {lib_path} " + " ".join(
            os.path.join(build_dir, o) for o in objs
        ))
        self.run(f"{ranlib} {lib_path}")

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        build_dir = self.build_folder

        # Headers
        for hdr in ("aes.h", "sha256.h", "password.h", "keyfile.h", "util.h",
                     "aescrypt.h", "version.h"):
            copy(self, hdr, src_dir, os.path.join(self.package_folder, "include"))

        # Static library
        copy(self, "libAESCryptPacketizer.a", build_dir, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["AESCryptPacketizer"]