#!/usr/bin/env python3
"""Conan recipe for microjson — a tiny JSON parser in C using fixed-extent storage.

microjson parses JSON into static C structures without using malloc(3).
It is intended for constrained embedded environments.

Source: https://github.com/Otteri/microjson
License: BSD-2-Clause
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MicrojsonConan(ConanFile):
    name = "microjson"
    version = "1.6"
    description = "A tiny JSON parser in C that uses only fixed-extent storage, no malloc"
    license = "BSD-2-Clause"
    homepage = "https://github.com/Otteri/microjson"
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

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "/data/service/hnp/bin/llvm-ar")
        ranlib = compilers.get("ranlib", "/data/service/hnp/bin/llvm-ranlib")

        src = self.source_folder
        # The Makefile has .SUFFIXES which disables built-in .c→.o rule,
        # so we compile mjson.o directly. Flags match upstream Makefile.
        self.run(f"{cc} -O -DDEBUG_ENABLE -g -DTIME_ENABLE -c -o mjson.o {src}/mjson.c")

        # Create static library from the compiled object
        self.run(f"{ar} rcs libmjson.a mjson.o")
        self.run(f"{ranlib} libmjson.a")

    def package(self):
        # Copy header from source, library from build folder
        copy(self, "mjson.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "libmjson.a", self.build_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["mjson"]
