#!/usr/bin/env python3
"""Conan recipe for jsonparse-cpp 1.00 — simple & fast JSON parser in ANSI C.

Upstream: https://github.com/liufeigit/jsonParse (tag v1.00).
The upstream project ships no build system (README instructs to compile
parse.c + object.c directly with clang/gcc), so this recipe performs the
compile manually, honoring R33 (compiler from Conan conf, never bare env).
Only a static library is produced; headers parse.h + object.h are installed.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class JsonparsecppConan(ConanFile):
    name = "jsonparse-cpp"
    version = "1.00"
    description = "jsonparse-cpp 1.00 — a simple and fast JSON parser in ANSI C (upstream jsonParse)"
    license = "MIT"
    homepage = "https://github.com/liufeigit/jsonParse"
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

        # R33: resolve the C compiler from Conan conf, never from bare ${CC}
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cflags = self.conf.get("tools.build:cflags", default=[], check_type=list)

        self.output.info(f"compiling with {cc}")
        self.run(f"{cc} {' '.join(cflags)} -fPIC -O2 -c parse.c object.c", cwd=self.source_folder)
        # The static archiver (llvm-ar) ships next to the toolchain compiler;
        # derive its path from the resolved compiler location (R33, no bare $AR).
        archiver = os.path.join(os.path.dirname(cc), "llvm-ar") if os.path.dirname(cc) else "llvm-ar"
        self.run(f"{archiver} -r {os.path.join(self.build_folder, 'libjsonParse.a')} parse.o object.o", cwd=self.source_folder)

    def package(self):
        copy(self, "parse.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "object.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "libjsonParse.a", self.build_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["jsonParse"]
