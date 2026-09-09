#!/usr/bin/env python3
"""Conan recipe — proctools 0.4pre1

pgrep / pkill / pfind BSD process tools (OpenBSD native + Darwin port),
adapted to OHOS (Linux/musl) with a /proc-based backend.

Build system: plain GNU Makefile (rewritten from the original BSD
bsd.prog.mk/bsd.lib.mk layout; see patches/). No configure script.
License: BSD-3-Clause + BSD-4-Clause-UC (see LICENSE in the tarball).
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class ProctoolsConan(ConanFile):
    name = "proctools"
    version = "0.4pre1"
    description = "BSD process tools: pgrep, pkill and pfind (process finder) — /proc backend for OHOS"
    license = "BSD-3-Clause AND BSD-4-Clause-UC"
    homepage = "https://proctools.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pure C, zero third-party dependencies (W0)
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
        # R9: -j1 for old single-directory make projects
        self.run(f'make -j1 CC="{cc}"', cwd=self.source_folder)

    def package(self):
        # The rewritten GNU Makefile provides a DESTDIR-aware install target:
        #   bin/ + share/man/man1/ + share/man/proctools/ + share/doc/proctools/
        self.run(
            f'make install DESTDIR="{self.package_folder}" PREFIX= -j1',
            cwd=self.source_folder,
        )

    def package_info(self):
        # Command-line tool suite, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
