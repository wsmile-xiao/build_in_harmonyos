#!/usr/bin/env python3
"""Conan recipe for samurai 1.3 — ninja-compatible build tool written in C99.

samurai is a ninja-compatible build tool with a focus on simplicity, speed,
and portability. It produces a single executable `samu`.

Build system: POSIX Makefile (no configure script).
The Makefile respects CC, CFLAGS, LDFLAGS, LDLIBS from the environment.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class SamuraiConan(ConanFile):
    name = "samurai"
    version = "1.3"
    description = "Ninja-compatible build tool written in C"
    license = "Apache-2.0"
    homepage = "https://git.sr.ht/~mcf/samurai"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Build in source directory — samurai's Makefile is in the source root
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain generates CC, CFLAGS, LDFLAGS env vars from the
        # Conan profile. R33: All flags come from Conan toolchain, no shell
        # env vars in build().
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R9: Always use -j1
        # CC, CFLAGS, LDFLAGS come from Conan toolchain (conanbuildenv)
        self.run("make -j1")

    def package(self):
        # samurai is a CLI tool — copy binary and man page
        copy(self, "samu", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "samu.1", src=self.build_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # Application: expose bin/ for consumers
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
