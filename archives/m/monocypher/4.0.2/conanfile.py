#!/usr/bin/env python3
"""Conan recipe — monocypher 4.0.2 (pure C crypto library).

Build system: raw Makefile (no configure script).  Targets:
  make library  -> lib/libmonocypher.a + lib/libmonocypher.so*
  make check    -> builds tests/test.c and runs ./test.out (upstream suite)
  make install  -> not used; package() copies artifacts directly.

Notes:
  - Upstream default CFLAGS contains -march=native (non-portable on CI
    workers); we pass an explicit portable CFLAGS instead.
  - R33: compiler comes from Conan conf, never from shell env vars.
  - R34: test_package exercises the real crypto_blake2b API with a known
    vector (upstream 4.0 removed crypto_sha512; BLAKE2b is the primary hash).
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get, copy, save, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.layout import basic_layout


class MonocypherConan(ConanFile):
    name = "monocypher"
    version = "4.0.2"
    description = "Easy to use, easy to deploy crypto library (X25519, EdDSA, BLAKE2b, Argon2, ChaCha20, Poly1305)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/LoupVaillant/Monocypher"
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

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler comes from Conan conf (dict form), never shell env vars.
        execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = execs.get("c", "clang")
        ar = execs.get("ar", "llvm-ar")
        ranlib = execs.get("ranlib", "llvm-ranlib")
        # Upstream default CFLAGS adds -march=native; pass portable flags.
        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} CFLAGS='-O2 -fPIC' -j1 library",
                 cwd=self.source_folder)
        # Upstream test suite (tests/test.c + tests/vectors.h from release tarball)
        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} CFLAGS='-O2 -fPIC' -j1 check",
                 cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        copy(self, "monocypher.h", src=os.path.join(src, "src"),
             dst=os.path.join(pkg, "include"))
        copy(self, "monocypher-ed25519.h", src=os.path.join(src, "src", "optional"),
             dst=os.path.join(pkg, "include"))
        if self.options.shared:
            copy(self, "libmonocypher.so*", src=os.path.join(src, "lib"),
                 dst=os.path.join(pkg, "lib"), keep_path=False)
        else:
            copy(self, "libmonocypher.a", src=os.path.join(src, "lib"),
                 dst=os.path.join(pkg, "lib"), keep_path=False)
        # Relocatable pkg-config file (upstream .pc uses a /PREFIX placeholder).
        pc = """prefix=${pkg_prefix}
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include

Name: monocypher
Version: 4.0.2
Description: Easy to use, easy to deploy crypto library
Libs: -L${libdir} -lmonocypher
Cflags: -I${includedir}
"""
        save(self, os.path.join(pkg, "lib", "pkgconfig", "monocypher.pc"), pc)

    def package_info(self):
        self.cpp_info.libs = ["monocypher"]
