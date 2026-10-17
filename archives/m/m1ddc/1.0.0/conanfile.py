#!/usr/bin/env python3
"""Conan recipe — m1ddc 1.0.0 (Makefile / single-file Objective-C CLI)

DDC/CI display control tool for Apple Silicon Macs (waydabber/m1ddc).
Builds the single m1ddc.m source into the `m1ddc` executable.

Build system: plain Makefile (single `clang -fmodules` invocation), no configure.
License: MIT
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class M1ddcConan(ConanFile):
    name = "m1ddc"
    version = "1.0.0"
    description = "Control external displays via DDC/CI (brightness, volume, contrast, input) on Apple Silicon Macs"
    license = "MIT"
    homepage = "https://github.com/waydabber/m1ddc"
    url = "https://github.com/waydabber/m1ddc"

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
        # Apply 0001-portable-nonapple.patch: m1ddc.m is split into
        # #ifdef __APPLE__ (original) + portable C implementation. Without the
        # patch the OHOS clang build dies at "@import Darwin" (module not found).
        apply_conandata_patches(self)
        # R33: resolve the C compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # Faithful to upstream Makefile: clang -fmodules -o m1ddc m1ddc.m
        # (-fmodules is inert once the @import lines are excluded on non-Apple)
        self.run(f"{cc} -fmodules -o m1ddc m1ddc.m", cwd=self.source_folder)

    def package(self):
        # m1ddc is a command-line tool: install the binary to bin/
        copy(self, "m1ddc", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
