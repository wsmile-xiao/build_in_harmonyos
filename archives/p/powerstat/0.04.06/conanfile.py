#!/usr/bin/env python3
"""Conan recipe — powerstat 0.04.06 (raw Makefile project, CLI tool).

Build notes:
  - powerstat is a single-source C project with a plain Makefile (no configure).
  - R33: compiler comes from Conan conf, never from shell env vars.
  - R9:  always -j1.
  - E119: linux/socket.h vs sys/socket.h sockaddr_storage redefinition is
          fixed in patches/0001-powerstat.c.patch via macro guard.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PowerstatConan(ConanFile):
    name = "powerstat"
    version = "0.04.06"
    description = "powerstat measures a computer's power consumption by sampling the system's battery and power domains"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ColinIanKing/powerstat"
    url = "https://github.com/ColinIanKing/powerstat"  # CI fills upstream repo

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
        compilers = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = compilers.get("c", "clang")
        # Raw Makefile project (no configure): build in the source folder,
        # since the upstream Makefile does not support out-of-source builds.
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "powerstat", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "powerstat.8.gz", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "powerstat", os.path.join(self.source_folder, "bash-completion"),
             os.path.join(self.package_folder, "share", "bash-completion", "completions"))

    def package_info(self):
        # CLI tool: no libraries, only a binary in bin/
        self.cpp_info.bindirs = ["bin"]
