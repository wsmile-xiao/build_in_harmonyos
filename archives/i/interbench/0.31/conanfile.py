#!/usr/bin/env python3
"""Conan recipe for interbench 0.31 — interactivity benchmark (Makefile).

Upstream ships a plain Makefile (no configure/install targets); the recipe
builds with `make CC=<clang>` and stages the produced `interbench` binary.
Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class InterbenchConan(ConanFile):
    name = "interbench"
    version = "0.31"
    description = "interbench — interactivity benchmark for the Linux kernel"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ckolivas/interbench"
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

        # R33: compiler comes from Conan conf, never from bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: always -j1
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "interbench", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
