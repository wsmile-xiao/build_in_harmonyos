#!/usr/bin/env python3
"""Conan recipe for coremark 1.01 — EEMBC CoreMark benchmark (Makefile).

Build: plain Makefile (no configure), PORT_DIR=linux64 port layer.
Produces the `coremark` executable (CLI benchmark tool).
Adapted for HarmonyOS OHOS (aarch64-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CoremarkConan(ConanFile):
    name = "coremark"
    version = "1.01"
    description = "EEMBC CoreMark benchmark - industry standard embedded CPU benchmark"
    license = "SEE LICENSE IN LICENSE.md"
    homepage = "https://www.eembc.org/coremark/"
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

        # coremark: plain Makefile, no configure. linux64 port layer, iterations fixed.
        # Build only (compile+link); authoritative benchmark runs happen in
        # test_package (iterations=0 auto-tune keeps the >=10s valid window).
        self.run(
            f"make PORT_DIR=linux64 CC={cc} EXE='' XCFLAGS='-DITERATIONS=1000' compile link -j1",
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "coremark", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]