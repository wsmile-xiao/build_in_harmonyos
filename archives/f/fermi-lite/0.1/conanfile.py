#!/usr/bin/env python3
"""Conan recipe for fermi-lite 0.1 — C library for assembling Illumina short reads.

Build: make. Produces libfml.a (library) + fml-asm (command-line assembler).
Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FermiLiteConan(ConanFile):
    name = "fermi-lite"
    version = "0.1"
    description = "fermi-lite — a C library and tool for assembling Illumina short reads"
    license = "MIT"
    homepage = "https://github.com/lh3/fermi-lite"
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
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        self.run(f"make CC={cc} AR={ar} -j1", cwd=self.source_folder)

    def package(self):
        # Install the static library and public headers
        copy(self, "libfml.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        for hdr in ("fml.h", "ksw.h", "kseq.h", "khash.h"):
            copy(self, hdr, self.source_folder, os.path.join(self.package_folder, "include"))
        # Install the command-line assembler
        copy(self, "fml-asm", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["fml"]
        self.cpp_info.system_libs = ["m", "z", "pthread"]
        self.cpp_info.bindirs = ["bin"]