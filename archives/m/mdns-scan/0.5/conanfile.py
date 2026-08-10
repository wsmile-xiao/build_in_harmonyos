#!/usr/bin/env python3
"""Conan recipe for mdns-scan 0.5 — a simple mDNS/DNS-SD service scanner.

mdns-scan is a command-line tool by Lennart Poettering that scans for
mDNS/DNS-SD published services on the local network. It has no external
dependencies besides the C library.

Build system: raw Makefile (no configure script).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MdnsScanConan(ConanFile):
    name = "mdns-scan"
    version = "0.5"
    description = "A tool for scanning for mDNS/DNS-SD published services on the local network"
    license = "GPL-2.0-or-later"
    homepage = "https://0pointer.de/lennart/projects/mdns-scan/"
    url = ""  # CI fills this

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
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        # Raw Makefile project (no configure script)
        # R9: Always use -j1
        self.run(f'make CC="{cc}" -j1', cwd=self.source_folder)

    def package(self):
        # Install the binary to bin/
        copy(self, "mdns-scan", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Install man page
        copy(self, "mdns-scan.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
