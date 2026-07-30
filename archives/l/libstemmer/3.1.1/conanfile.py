#!/usr/bin/env python3
"""Conan recipe for libstemmer 3.1.1 — Makefile build system.

libstemmer is the C version of the Snowball stemming library,
providing multilingual word stemming algorithms.

Build system: simple Makefile (no configure script).
Products: libstemmer.a (static library), stemwords (example binary).
License: BSD-3-Clause
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibStemmerConan(ConanFile):
    name = "libstemmer"
    version = "3.1.1"
    description = "Multilingual stemming library (Snowball C implementation)"
    license = "BSD-3-Clause"
    homepage = "https://snowballstem.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # R32: OHOS platform compatibility — must use in, not ==
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

    def build(self):
        apply_conandata_patches(self)
        # R9: Use -j1 (OHOS parallel constraint)
        self.run("make CC=clang AR=llvm-ar -j1")

    def package(self):
        # Install the static library and public header
        copy(self, "libstemmer.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libstemmer.h", src=os.path.join(self.build_folder, "include"), dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["stemmer"]
