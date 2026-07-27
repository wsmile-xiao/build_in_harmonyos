#!/usr/bin/env python3
"""Conan recipe — zopfli 1.0.3 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ZopfliConan(ConanFile):
    name = "zopfli"
    version = "1.0.3"
    description = "Google's compression library producing smaller gzip/zlib outputs than standard zlib"
    license = "Apache-2.0"
    homepage = "https://github.com/google/zopfli"
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

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"

        self.run(f"make CC={cc} CXX={cxx} -j1")

    def package(self):
        copy(self, "*.h", os.path.join(self.source_folder, "src", "zopfli"),
             os.path.join(self.package_folder, "include", "zopfli"))

        if self.options.shared:
            copy(self, "libzopfli.so*", self.source_folder, os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libzopfli.a", self.source_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["zopfli"]
