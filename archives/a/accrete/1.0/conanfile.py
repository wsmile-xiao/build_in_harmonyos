#!/usr/bin/env python3
"""Conan recipe — accrete 1.0

Physical simulation of solar system planet formation.
Originally published to Usenet (comp.sources.unix) in 1991 by Joe Nowakowski.
Public domain (FreeBSD ports declare BSD-3-Clause; mtrng.c is BSD-style).

Build system: plain Makefile (no configure). `make` produces the `accrete`
command-line tool; running it writes the generated system to `New.System`.

OHOS specifics:
  - The Makefile's default `INSTALL = /usr/bin/install -s` does not exist on
    OHOS, so install is replaced by copying the binary directly in package().
  - Compiler is taken from Conan conf (R33), never bare shell env vars.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AccreteConan(ConanFile):
    name = "accrete"
    version = "1.0"
    description = "Physical simulation of solar system planet formation (Joe Nowakowski 1991, public domain)"
    license = "BSD-3-Clause"
    homepage = "https://sourceforge.net/projects/accrete/"
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

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # R9: always -j1 for this small single-directory project
        # -m is not needed: math functions resolve from libc on OHOS
        self.run(f'make -j1 CC="{cc}" CFLAGS="-O2" LDFLAGS=""', cwd=self.source_folder)

    def package(self):
        # The Makefile install target relies on /usr/bin/install (absent on OHOS).
        # accrete is a command-line tool: copy the binary straight into bin/.
        copy(self, "accrete", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
