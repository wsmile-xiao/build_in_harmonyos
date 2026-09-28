#!/usr/bin/env python3
"""Conan recipe for lgrind 3.67 — LaTeX source-code pretty-printer (plain Makefile).

Builds the `lgrind` binary from source/ (top-level Makefile targets need TeX,
which is out of scope on OHOS). Produces:
  bin/lgrind        — the pretty-printer tool (application, R38: commands.json)
  res/lgrindef      — runtime language-definition database, consumed via -d
The compile-time DEFSFILE default points into the package res dir, so the
installed tool resolves its definitions without flags; -d <file> overrides.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LgrindConan(ConanFile):
    name = "lgrind"
    version = "3.67"
    description = "lgrind — produces LaTeX listings from source code (vgrind successor)"
    license = "BSD-4-Clause"
    homepage = "https://ctan.org/pkg/lgrind"
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

        # R32: os=OHOS is the adaptation target; allow Linux for local parity
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lgrind OHOS adaptation supports os=Linux/OHOS only")

        # R33: compiler must come from Conan conf, never bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        defsfile = os.path.join(self.package_folder, "res", "lgrindef")
        srcdir = os.path.join(self.source_folder, "source")
        # R1/R9: minimal params, only what the Makefile requires; -j1 per iron rule
        self.run(
            f'make CC={cc} CFLAGS="-O2" '
            f'DEFSFILE="{defsfile}" VERSION="{self.version}" -j1',
            cwd=srcdir,
        )
        # retest/v2lg are upstream dev helpers; not shipped (retest needs its
        # own link variant per notes.md, product binary is unaffected).

    def package(self):
        srcdir = self.source_folder
        copy(self, "lgrind", os.path.join(srcdir, "source"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "lgrindef", srcdir, os.path.join(self.package_folder, "res"))
        copy(self, "lgrind.1", os.path.join(srcdir, "source"),
             os.path.join(self.package_folder, "res", "man", "man1"))
        copy(self, "lgrindef.5", os.path.join(srcdir, "source"),
             os.path.join(self.package_folder, "res", "man", "man5"))

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
        # bindir on PATH so consumers can invoke `lgrind` directly
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
