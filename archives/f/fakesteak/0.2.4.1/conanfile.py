#!/usr/bin/env python3
"""Conan recipe for fakesteak 0.2.4.1 — Matrix digital rain for your terminal.

A lightweight C implementation of the Matrix digital rain effect,
using ANSI escape codes. No dependencies (not even ncurses).

Build system: simple Makefile (no configure script).
License: CC0-1.0 (Public Domain)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.env import VirtualBuildEnv


class FakesteakConan(ConanFile):
    name = "fakesteak"
    version = "0.2.4.1"
    description = "Matrix digital rain for your terminal (no ncurses dependency)"
    license = "CC0-1.0"
    homepage = "https://github.com/domsson/fakesteak"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
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

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, never hardcode or use shell env vars
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang") if comp else "clang"
        # Use -j1 to avoid race conditions; CFLAGS/LDLIBS handled by Makefile after patch
        self.run(f"make CC='{cc}' -j1", env="conanbuild")

    def package(self):
        # Copy the fakesteak executable to bin/
        copy(self, "fakesteak", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # CLI tool — no libraries, just executables
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
