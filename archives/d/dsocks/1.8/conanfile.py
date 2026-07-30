#!/usr/bin/env python3
"""Conan recipe — dsocks 1.8 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DsocksConan(ConanFile):
    name = "dsocks"
    version = "1.8"
    description = "SOCKS client wrapper library using LD_PRELOAD to intercept connect/getaddrinfo/gethostbyname"
    license = "BSD-style"
    homepage = "http://monkey.org/~dugsong/dsocks/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        self.run(f"make -f GNUMakefile CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # Use make install to create proper symlinks (R5: rm -f && ln -s)
        self.run(f"make -f GNUMakefile install DESTDIR={self.package_folder} LIBDIR=/lib BINDIR=/bin", cwd=self.source_folder)
        copy(self, "dsocks.h", self.source_folder, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["dsocks"]
