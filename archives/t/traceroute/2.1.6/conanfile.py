#!/usr/bin/env python3
"""Conan recipe for traceroute 2.1.6 — Makefile build system, network route tracing tool.

traceroute is a TCP/IP network route tracing utility that traces the path
packets take from source to destination. Supports UDP, ICMP, TCP, and DCCP
probe methods.

Homepage: https://traceroute.sourceforge.net/
License: GPL-2.0-or-later
"""

import os
import stat

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TracerouteConan(ConanFile):
    name = "traceroute"
    version = "2.1.6"
    description = "Modern traceroute for Linux, supports UDP, ICMP, TCP, DCCP"
    license = "GPL-2.0-or-later"
    homepage = "https://traceroute.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
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
        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: Always use -j1
        # env=yes: allow Makefile to accept command-line variable overrides
        # LDFLAGS: use --ld-path to bypass broken lld on CI workers (libxml2.so.16 missing)
        ld = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("ld", "/data/service/hnp/bin/ld")
        self.run(f'make env=yes CC="{cc}" LDFLAGS="-s --ld-path={ld}" -j1', cwd=self.source_folder)

    def package(self):
        # Install binary and man page via Makefile install target
        self.run(f'make install prefix={self.package_folder} INSTALL="install -m 755"', cwd=self.source_folder)

    def package_info(self):
        # traceroute is a standalone binary tool, no libraries to export
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
