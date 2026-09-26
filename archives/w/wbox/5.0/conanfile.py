#!/usr/bin/env python3
"""Conan recipe — wbox 5.0 (Wbox HTTP testing tool).

wbox is a small ANSI C / POSIX tool by Salvatore 'antirez' Sanfilippo used to
benchmark and stress HTTP servers, to check virtual host / redirect / HTTP
compression setups, and to serve a directory tree as a configuration-less
HTTP server:

    wbox www.example.com 10          # 10 HTTP requests, timings
    wbox servermode webroot /tmp     # serve /tmp over HTTP on port 8081

Build system: plain Makefile (`all` / `clean` / `dep`, no configure step, no
generated headers, no third-party dependencies — only libc + POSIX sockets,
fork() and signals).  The source compiles as-is with the OHOS clang toolchain
and needs no patches.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class WboxConan(ConanFile):
    name = "wbox"
    # Upstream identifies this release as plain "5" (tarball wbox-5.tar.gz,
    # `wbox -v` prints "WBox version 5"). Conan 2.29.1 rejects single-character
    # versions (`Invalid package version '5'`, refs.py:148 pattern requires
    # >=2 chars), so the version is normalised to "5.0" — same convention as
    # the repository precedent btyacc (upstream "3" -> recipe "3.0").
    version = "5.0"
    description = ("Wbox HTTP testing tool — HTTP client benchmarking/stressing "
                   "(timings, virtual hosts, redirects, compression) plus a "
                   "configuration-less HTTP server mode")
    license = "BSD-3-Clause"
    homepage = "https://www.hping.org/wbox/"
    url = ""  # CI fills this

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

        # R33: compiler and flags come from the Conan toolchain — the release
        # worker's shell environment has no CC/CFLAGS of its own.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cflags = self.conf.get("tools.build:cflags", default=[], check_type=list)
        cflags = " ".join(cflags) if cflags else "-O2 -Wall -W"

        # Upstream Makefile: wbox: $(OBJ) -> $(CC) -o wbox $(CCOPT) $(DEBUG) $(OBJ)
        # DEBUG is cleared so Release packages carry no -g debug info (which
        # would otherwise embed host build paths). R9: build with -j1.
        self.run(f'make CC="{cc}" CFLAGS="{cflags}" DEBUG="" -j1',
                 cwd=self.source_folder)

    def package(self):
        copy(self, "wbox", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "Changelog", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "wbox"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "wbox"))

    def package_info(self):
        # CLI application: only bin/ is populated, no headers or libraries.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
