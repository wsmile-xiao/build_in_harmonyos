#!/usr/bin/env python3
"""Conan recipe for LAST (last-align) 1652 — plain Makefile C++ application.

LAST is a bioinformatics tool for large-scale sequence alignment, built from
a plain Makefile (top-level `makefile` delegates to `src/makefile`).  It is
NOT an autotools project (there is no configure script).

Key build facts:
  * Build command: `make -j1` at the source root (writes binaries into bin/).
  * Install: `make install prefix=<...>` copies bin/* to <prefix>/bin.
  * CXXFLAGS default contains `-msse4` (x86-only).  On aarch64 clang it is
    merely an unused-argument warning, but we pass our own flags to be safe.
  * The SIMD code (src/mcf_simd.hh) auto-selects the NEON path on aarch64.
  * Link uses `-lz`; zlib is declared as a Conan dependency and its
    include/lib dirs are injected via CPPFLAGS/LDFLAGS (R18/R26).
"""
import os
import shlex

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LastAlignConan(ConanFile):
    name = "last-align"
    version = "1652"
    description = (
        "LAST: large-scale genome sequence comparison / alignment tool "
        "(lastdb, lastal, last-split, etc.)"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.com/mcfrith/last"
    url = ""  # CI fills this
    topics = ("bioinformatics", "alignment", "genome")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
        )

    @staticmethod
    def _quote(value):
        return shlex.quote(str(value))

    def _compiler(self, key, default):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get(key, default)

    def _make_arguments(self):
        cc = self._compiler("c", "clang")
        cxx = self._compiler("cpp", "clang++")

        cxxflags = ["-O3", "-std=c++11", "-pthread"]
        cflags = ["-Wall", "-O2"]

        include_flags = []
        libdir_flags = []
        if "zlib" in self.dependencies:
            cpp_info = self.dependencies["zlib"].cpp_info
            include_flags.extend(f"-I{path}" for path in cpp_info.includedirs)
            libdir_flags.extend(f"-L{path}" for path in cpp_info.libdirs)

        assignments = {
            "CC": cc,
            "CXX": cxx,
            "CFLAGS": " ".join(cflags),
            "CXXFLAGS": " ".join(cxxflags),
            "CPPFLAGS": " ".join(include_flags),
            "LDFLAGS": " ".join(libdir_flags),
        }
        return " ".join(f"{key}={self._quote(value)}" for key, value in assignments.items())

    def build(self):
        apply_conandata_patches(self)

        copy(
            self,
            "*",
            src=self.source_folder,
            dst=self.build_folder,
        )

        make_args = self._make_arguments()
        # Top-level makefile writes binaries into bin/ (relative to source root).
        self.run(
            f"make -j1 {make_args}",
            cwd=self.build_folder,
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "COPYING.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        copy(
            self,
            "*",
            src=os.path.join(self.build_folder, "bin"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        self.buildenv_info.prepend_path(
            "PATH",
            os.path.join(self.package_folder, "bin"),
        )
        self.runenv_info.prepend_path(
            "PATH",
            os.path.join(self.package_folder, "bin"),
        )
