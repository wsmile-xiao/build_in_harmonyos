#!/usr/bin/env python3
"""Conan recipe for cgranges 0.1.1 — C library for genomic interval overlap queries.

Build: make (no configure). Produces the libcgranges static library + cgranges.h
public header. Adapted for HarmonyOS OHOS (aarch64-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CgrangesConan(ConanFile):
    name = "cgranges"
    version = "0.1.1"
    description = "cgranges — a C library for genomic interval overlap queries"
    license = "MIT"
    homepage = "https://github.com/lh3/cgranges"
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

        # R33: get compiler from Conan conf, never from bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("lib", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("lib", "llvm-ranlib") if compilers else "llvm-ranlib"
        # R9: always -j1; build the library object from cgranges.c
        self.run(
            f"{cc} -fPIC -O2 -c cgranges.c -o cgranges.o && "
            f"{ar} rcs libcgranges.a cgranges.o && "
            f"{ranlib} libcgranges.a",
            cwd=self.source_folder,
        )

    def package(self):
        # static library + public header
        copy(self, "libcgranges.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "cgranges.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "khash.h", self.source_folder, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["cgranges"]
        self.cpp_info.includedirs = ["include"]