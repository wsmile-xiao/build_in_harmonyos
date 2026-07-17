#!/usr/bin/env python3
"""Conan recipe for fakesteak 0.2.4 — Matrix digital rain for your terminal.

A lightweight C implementation of the Matrix digital rain effect,
using ANSI escape codes. No dependencies (not even ncurses).

Build system: simple Makefile (no configure script).
License: CC0-1.0 (Public Domain)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class FakesteakConan(ConanFile):
    name = "fakesteak"
    version = "0.2.4"
    description = "Matrix digital rain for your terminal (no ncurses dependency)"
    license = "CC0-1.0"
    homepage = "https://github.com/domsson/fakesteak"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Build in source directory — Makefile is in the source root
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        # R32: Platform check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # OHOS profile always uses clang; R33: don't use shell env vars
        # R9: Always use -j1
        self.run('make CC=clang CFLAGS="-Wall -O3 -fPIC" LDLIBS="-lm" -j1')

    def package(self):
        # Copy the fakesteak executable to bin/
        copy(self, "fakesteak", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # CLI tool — no libraries, just executables
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
