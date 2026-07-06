#!/usr/bin/env python3
"""Conan recipe — sponge 0.70

sponge is part of moreutils. It soaks up all input from stdin and writes it
to a file, allowing safe read-modify-write patterns in shell pipelines.

Build system: simple Makefile (no configure script).
License: GPL-2.0-only
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class SpongeConan(ConanFile):
    name = "sponge"
    version = "0.70"
    description = "Soak up standard input and write to a file (from moreutils)"
    license = "GPL-2.0-only"
    homepage = "https://joeyh.name/code/moreutils/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # sponge is a standalone C tool, only depends on libc, no system lib collision risk
        pass

    def build(self):
        apply_conandata_patches(self)
        # sponge comes from moreutils; only build the sponge target
        # sponge.c includes physmem.c inline, so no separate compilation needed
        # R9: Always use -j1
        self.run('make sponge -j1 CC="${CC}" CFLAGS="${CFLAGS} -Wall"')

    def package(self):
        # Install the sponge binary
        copy(self, "sponge", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # sponge is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
