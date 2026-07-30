#!/usr/bin/env python3
"""Conan recipe for deark 1.7.2 — file format decoder and extraction tool.

deark is a command-line tool for decoding and extracting content from
various old/obscure file formats. It uses a pure Makefile build system
(no configure script) and has no external dependencies.

Build: make CC=clang CFLAGS="..." -j1
Install: manual copy of the deark binary (make install uses -s/strip
which removes ELF signatures on OHOS)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DearkConan(ConanFile):
    name = "deark"
    version = "1.7.2"
    description = "Portable command-line utility for decoding and extracting content from various old file formats"
    license = "MIT"
    homepage = "https://entropymine.com/deark/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # deark is a CLI tool, not a library
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"deark only supports Linux/OHOS, got {self.settings.os}"
            )

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, not from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # deark uses a pure Makefile — pass CC and CFLAGS directly.
        # CFLAGS match upstream defaults (see Makefile CFLAGS ?= line).
        cflags = "-fPIC -O2 -std=c99 -Wall -Wextra -Wmissing-prototypes -Wformat-security -Wno-unused-parameter"

        self.run(
            f'make CC="{cc}" CFLAGS="{cflags}" LDFLAGS="" -j1',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        # Copy the deark binary to bin/ — do NOT use make install
        # because it uses -s (strip) which removes ELF signatures on OHOS.
        copy(self, "deark", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # deark is a CLI tool — binary in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
