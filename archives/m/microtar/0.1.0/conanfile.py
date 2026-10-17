#!/usr/bin/env python3
"""Conan recipe — microtar 0.1.0 (custom clang build).

Two-file ANSI C tar library (src/microtar.c + src/microtar.h) with no
upstream build system; compiled directly with clang and archived with
llvm-ar. Static by default (R26).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MicrotarConan(ConanFile):
    name = "microtar"
    version = "0.1.0"
    description = "A lightweight tar library written in ANSI C"
    license = "MIT"
    homepage = "https://github.com/rxi/microtar"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        ar = compilers.get("ar") or "llvm-ar"
        cflags = "-fPIC -O2"
        if self.options.shared:
            self.run(
                f'{cc} {cflags} -I src -c src/microtar.c -o microtar.o',
                cwd=self.source_folder,
            )
            self.run(
                f'{cc} -shared microtar.o -o libmicrotar.so',
                cwd=self.source_folder,
            )
        else:
            self.run(
                f'{cc} {cflags} -I src -c src/microtar.c -o microtar.o',
                cwd=self.source_folder,
            )
            self.run(f'{ar} rcs libmicrotar.a microtar.o', cwd=self.source_folder)

    def package(self):
        copy(self, "microtar.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libmicrotar.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libmicrotar.so", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["microtar"]
