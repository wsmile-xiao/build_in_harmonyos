#!/usr/bin/env python3
"""Conan recipe for atasm 1.30 — Atari MAC/65 compatible assembler.

Build system: plain Makefile (no configure script).
This recipe enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AtasmConan(ConanFile):
    name = "atasm"
    version = "1.30"
    description = "Atari MAC/65 compatible assembler for Unix"
    license = "MIT"
    homepage = "https://github.com/CycoPH/atasm"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Terminal tools must be statically linked
        # atasm is a terminal tool — BUILD_SHARED_LIBS=OFF
        env = {
            "CC": str(self.settings.compiler) if self.settings.compiler else "clang",
            "BUILD_SHARED_LIBS": "OFF",
            "CFLAGS": f"-Wall -DUNIX -fPIC -O2",
            "LDFLAGS": "-static",
        }
        self._env = env

    def build(self):
        apply_conandata_patches(self)
        src_dir = os.path.join(self.source_folder, "src")
        # Build atasm and verify binaries using the plain Makefile
        self.run(f'make -C {src_dir} CC=clang CFLAGS="-Wall -DUNIX -fPIC -O2" LDFLAGS="-static"')

    def package(self):
        # Copy binaries
        copy(self, "atasm", src=os.path.join(self.source_folder, "src"), dst=os.path.join(self.package_folder, "bin"))
        # Copy man page
        copy(self, "atasm.1.in", src=os.path.join(self.source_folder, "src"), dst=os.path.join(self.package_folder, "share", "man", "man1"))
        # Copy docs
        copy(self, "atasm.txt", src=os.path.join(self.source_folder, "docs"), dst=os.path.join(self.package_folder, "share", "doc", "atasm"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
