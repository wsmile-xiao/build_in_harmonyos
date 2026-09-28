#!/usr/bin/env python3
"""Conan recipe — chal 1.1.0

Chal: single-file C99 chess engine with full FIDE rules and UCI support.
https://github.com/namanthanki/chal

Build system: plain Makefile (src/chal.c → bin/chal), no configure script.
License: MIT (see LICENSE in upstream tarball)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class ChalConan(ConanFile):
    name = "chal"
    version = "1.1.0"
    description = "Single-file chess engine under 1k LoC of C99 with full FIDE rules and UCI support"
    license = "MIT"
    homepage = "https://github.com/namanthanki/chal"
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
        # R9: always -j1 for old single-file make projects
        self.run(f'make -j1 CC="{cc}"', cwd=self.source_folder)

    def package(self):
        # chal is a command-line tool (UCI chess engine): install the binary to bin/
        # pattern "bin/chal" keeps the relative path, so dst is the package root
        copy(self, "bin/chal", src=self.source_folder, dst=self.package_folder)

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
