#!/usr/bin/env python3
"""Conan recipe for raxml 8.2.13 (standard-RAxML) on HarmonyOS PC.

RAxML is a CLI tool (phylogenetic inference) built with hand-written
Makefiles (no configure, no install target). We use Makefile.gcc which
already has an aarch64 branch (ARCH_CFLAGS= empty) and ships sse2neon.h
for NEON translation. Output binary: raxmlHPC.
"""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RaxmlConan(ConanFile):
    name = "raxml"
    version = "8.2.13"
    description = "RAxML: Randomized Axelerated Maximum Likelihood phylogenetic inference tool"
    license = "GPL-3.0-only"
    homepage = "https://github.com/stamatak/standard-RAxML"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pure C build; only -lm (system libm), no external conan deps
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: get compiler from Conan conf, never from shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # Serial build with -j1 (per project convention); Makefile.gcc has an
        # aarch64 branch already (ARCH_CFLAGS=). The Makefile defines its own
        # CFLAGS (-D_GNU_SOURCE -O2 ...); we only inject the compiler via CC
        # (R33: from Conan conf, not shell env).
        self.run(f"make -f Makefile.gcc CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # No upstream install target: manually place the CLI binary
        copy(self, "raxmlHPC", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "share", "doc", "raxml"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
