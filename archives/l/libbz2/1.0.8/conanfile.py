#!/usr/bin/env python3
"""Conan recipe for libbz2 1.0.8 — Makefile build system.

libbz2 (upstream bzip2) is a data compression library and tool set.
Build: make && make install
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Bzip2Conan(ConanFile):
    name = "libbz2"
    version = "1.0.8"
    description = "High-quality data compression library and tools."
    license = "BSD-4-Clause"
    homepage = "https://sourceware.org/bzip2/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os == "OHOS" and self.options.shared:
            raise ConanInvalidConfiguration(
                "bzip2 shared=True is disabled on OHOS because Makefile-libbz2_so "
                "uses symlink logic that is unsafe on HMDFS; use the static package."
            )

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
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        self.run(
            f"make CC={cc} CXX={cxx} AR=llvm-ar RANLIB=llvm-ranlib SHELL={config_shell} -j1",
            cwd=self.source_folder,
        )

    def package(self):
        pkg = self.package_folder
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f"make install PREFIX={pkg} SHELL={config_shell}",
            cwd=self.source_folder,
        )

    def package_info(self):
        self.cpp_info.libs = ["bz2"]
        self.cpp_info.bindirs = ["bin"]
