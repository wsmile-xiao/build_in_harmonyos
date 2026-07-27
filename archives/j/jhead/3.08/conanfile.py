#!/usr/bin/env python3
"""Conan recipe for jhead 3.08 — JPEG Exif header manipulation tool.

jhead is a command-line tool for displaying and manipulating Exif header
data embedded in JPEG images from digital cameras. It uses a simple Makefile
(no configure script) and has no external dependencies beyond libc and libm.

Upstream: https://github.com/Matthias-Wandel/jhead
License: Public Domain
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class JheadConan(ConanFile):
    name = "jhead"
    version = "3.08"
    description = "Extract and manipulate Exif header data from JPEG images"
    license = "Public Domain"
    homepage = "https://github.com/Matthias-Wandel/jhead"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jhead only supports Linux/OHOS, got {self.settings.os}"
            )

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # R9: Always use -j1
        self.run(
            f'make CC="{cc}" -j1',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        # Install with PREFIX= so binary goes to bin/ (not usr/local/bin/)
        self.run(
            f'make install DESTDIR="{self.package_folder}" PREFIX= BINDIR=/bin DOCDIR=/share/doc/jhead MANDIR=/share/man/man1',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package_info(self):
        # jhead is a CLI tool — binary in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
