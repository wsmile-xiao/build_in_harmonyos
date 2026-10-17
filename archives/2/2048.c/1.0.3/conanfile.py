#!/usr/bin/env python3
"""Conan recipe for 2048.c 1.0.3 — single-file C console game (Makefile).

Build: make && make install. Produces the `2048` executable (console game).
Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Game2048CConan(ConanFile):
    name = "2048.c"
    version = "1.0.3"
    description = "2048.c — console version of the game 2048 for GNU/Linux (single-file C)"
    license = "MIT"
    homepage = "https://github.com/mevdschee/2048.c"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        apply_conandata_patches(self)

        # R33: get compiler from Conan conf, never from bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: always -j1
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # Makefile install writes $(DESTDIR)$(PREFIX)/bin; place binary at pkg/bin
        copy(self, "2048", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
