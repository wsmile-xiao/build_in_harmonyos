#!/usr/bin/env python3
"""Conan recipe — lzd 1.5 (single-file C++98 CLI, educational lzip decompressor).

lzd (Antonio Diaz Diaz) is the reference educational decompressor for the
lzip format: one 492-line C++98 source, custom POSIX configure + Makefile.in
(no autoconf), zero dependencies. Ships a REAL upstream test suite
(testsuite/check.sh with fox*.lz/em.lz fixtures) which this recipe runs via
`make check` in build() (R51, CI L1c).
"""
from conan import ConanFile
import os

from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class LzdConan(ConanFile):
    name = "lzd"
    version = "1.5"
    description = "Educational decompressor for the lzip format (single-file C++98 CLI)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/lzip/lzd.html"
    url = "https://download.savannah.gnu.org/releases/lzip/lzd/"
    topics = ("lzip", "compression", "cli", "educational")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass  # in-source build, single tree

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cxx = (self.conf.get("tools.build:compiler_executables") or {}).get("cpp", "clang++")
        self.run(f'./configure CXX="{cxx}" CXXFLAGS="-O2" --prefix={self.package_folder}',
                 env="conanbuild")
        self.run("make -j1", env="conanbuild")
        # Upstream official test suite (R51): fox*.lz + em.lz fixtures
        self.run("make check", env="conanbuild")

    def package(self):
        # upstream tarball ships no doc/lzd.1 (man page needs makeinfo); bin only
        self.run("make install-bin", env="conanbuild")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []

