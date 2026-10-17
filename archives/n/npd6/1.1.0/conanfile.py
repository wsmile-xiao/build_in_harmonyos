#!/usr/bin/env python3
"""Conan recipe — npd6 1.1.0

Neighbor Proxy Daemon IPv6 — provides NDP proxy functionality for IPv6
networks, responding to Neighbor Solicitation messages on behalf of
non-local addresses.

Build system: plain Makefile (no configure script).
License: GPL-3.0-only
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class Npd6Conan(ConanFile):
    name = "npd6"
    version = "1.1.0"
    description = "Neighbor Proxy Daemon IPv6 — NDP proxy for IPv6 networks"
    license = "GPL-3.0-only"
    homepage = "https://github.com/npd6/npd6"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # -fcommon: npd6.h defines globals without extern (common symbol behavior)
        # -fPIC: required for OHOS
        cflags = "-Wall -g -O3 -fPIC -fcommon"
        self.run(f'make -j1 CC="{cc}" CFLAGS="{cflags}"', cwd=self.source_folder)

    def package(self):
        # Use Makefile install target to properly install binary + config + man pages
        # (avoids copy() matching both source_folder/npd6 binary and etc/npd6 init script)
        self.run(f"make install DESTDIR={self.package_folder} INSTALL_PREFIX=/usr", cwd=self.source_folder)

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["usr/bin"]
