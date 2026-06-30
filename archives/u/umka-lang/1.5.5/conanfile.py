#!/usr/bin/env python3
"""Conan recipe for umka-lang 1.5.5 — Makefile-based build.

umka-lang uses a plain Makefile (not autotools). The Makefile detects
the platform via `uname -s`, which returns "HarmonyOS" on OpenHarmony.
We override PLATFORM=Linux to select the correct build flags.

R26: The umka binary is statically linked with libumka.a (-DUMKA_STATIC).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class UmkaLangConan(ConanFile):
    name = "umka-lang"
    version = "1.5.5"
    description = "Umka: a statically typed embeddable scripting language"
    license = "BSD-2-Clause"
    homepage = "https://github.com/vtereshkov/umka-lang"
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
        # The umka binary is built with -DUMKA_STATIC and links libumka.a
        pass

    def build(self):
        apply_conandata_patches(self)
        # umka-lang uses a plain Makefile (not autotools)
        # Run make in the source folder where the Makefile is located
        # PLATFORM=Linux for HarmonyOS compatibility (uname -s returns "HarmonyOS")
        self.run("make -j1 PLATFORM=Linux", cwd=self.source_folder)

    def package(self):
        # Install to Conan package folder
        self.run(f"make install PLATFORM=Linux PREFIX={self.package_folder}",
                 cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["umka"]
