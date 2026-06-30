#!/usr/bin/env python3
"""Conan recipe — lzsa 1.4.1 (plain Makefile, no configure).

lzsa is a lossless packer optimized for fast decompression on 8-bit micros.
Build system: plain Makefile (CC=clang, no configure script, no install target).

R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF).
R27: No external dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class LzsaConan(ConanFile):
    name = "lzsa"
    version = "1.4.1"
    description = "Lossless packer optimized for fast decompression on 8-bit micros"
    license = "MIT"
    homepage = "https://github.com/emmanuel-marty/lzsa"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        # Try local tarball first (for offline/restricted-network builds),
        # fall back to URL download from conandata.yml
        import os, glob
        candidates = []
        candidates += glob.glob(os.path.expanduser("~/tmp/builds/lzsa-1.4.1.tar.gz"))
        td = os.environ.get("TMPDIR", "")
        if td:
            candidates += glob.glob(os.path.join(td, "builds", "lzsa-1.4.1.tar.gz"))
        for c in candidates:
            if os.path.isfile(c):
                get(self, "file://" + os.path.abspath(c),
                    sha256=self.conan_data["sources"]["sha256"], strip_root=True)
                return
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Terminal tools must be statically linked
        # Pass LDFLAGS=-static as make argument since Makefile overrides LDFLAGS
        pass

    def build(self):
        apply_conandata_patches(self)
        # Plain Makefile — no configure step
        # Pass LDFLAGS=-static on make command line to override Makefile's LDFLAGS=
        self.run("make -j1 LDFLAGS=-static")

    def package(self):
        # No 'make install' target — manually copy binary
        copy(self, "lzsa", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["lzsa"]
        self.cpp_info.bindirs = ["bin"]
