#!/usr/bin/env python3
"""Conan recipe for as31 2.0beta3 — Intel 8031/8051 Assembler.

as31 is a self-contained CLI assembler with no external dependencies.
The upstream Makefile uses CC=gcc and builds both CLI (as31) and GTK
GUI (as31_gtk). We override CC with clang and build only the CLI target.
The official source from pjrc.com does not include pre-generated parser.c,
so bison is used to generate it from parser.y during build.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class As31Conan(ConanFile):
    name = "as31"
    version = "2.0beta3"
    description = "Intel 8031/8051 Assembler"
    license = "BSD"
    homepage = "https://www.pjrc.com/tech/8051/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R32: Support both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")
        # R33: Get compiler from Conan conf, never from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # Official source has parser.y but not parser.c — generate with bison
        bison = "bison"
        self.run(f'{bison} -d -o parser.c parser.y')
        # Build only the CLI binary (as31), not as31_gtk (requires GTK)
        # Source files: run.c, lexer.c, parser.c, symbol.c, emitter.c, as31.c
        self.run(f'"{cc}" -O3 -Wall -c run.c lexer.c parser.c symbol.c emitter.c as31.c')
        self.run(f'"{cc}" -o as31 run.o lexer.o parser.o symbol.o emitter.o as31.o')

    def package(self):
        copy(self, "as31", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
