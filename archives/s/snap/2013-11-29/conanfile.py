#!/usr/bin/env python3
"""Conan recipe for SNAP 2013-11-29 — KorfLab Semi-HMM gene prediction tools.

Bare-Makefile C project (no configure step upstream): builds the five CLI tools
(snap, fathom, forge, hmm-info, exonpairs) by invoking the app targets directly
with CC/CFLAGS overrides, so the Makefile's own pattern rule consumes toolchain
flags. Two deliberate deviations from the upstream `make gcc` default target:

- The `gcc` target hardcodes CC="gcc" and -Werror; the device/CI toolchain is
  clang, so the target is bypassed instead of patched.
- CFLAGS carries -fcommon: the Zoe library's file-scope tentative definitions
  (zoeFunction/zoeConstructor/zoeMethod, repeated in snap.c and several Zoe/*.c)
  collide under -fno-common (default since clang 11 / gcc 10 — the same class
  of breakage upstream fixed after 2013 in its "gcc10-fix" commit).

Source URL is the Debian pool .orig tarball; the full sourcing evidence chain
(official site dead, GitHub history lacks this version, mirrors checked) is in
notes.md. Stock HMM parameter sets are shipped under res/HMM as runtime data.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SnapConan(ConanFile):
    name = "snap"
    version = "2013-11-29"
    description = "SNAP - Semi-HMM-based Nucleic Acid Parser (KorfLab gene prediction CLI tools)"
    license = "MIT"
    homepage = "https://github.com/KorfLab/SNAP"
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

        # R33: compiler/flags must come from Conan conf, never bare shell env
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        extra = self.conf.get("tools.build:cflags", default=[], check_type=list)
        cflags = " ".join(["-O2", "-fcommon"] + list(extra))

        targets = "snap fathom forge hmm-info exonpairs"
        self.run(
            f'make CC="{cc}" CFLAGS="{cflags}" {targets} -j1',
            cwd=self.source_folder,
        )

    def package(self):
        for tool in ("snap", "fathom", "forge", "hmm-info", "exonpairs"):
            copy(self, tool, self.source_folder,
                 os.path.join(self.package_folder, "bin"))
        # Stock HMM parameter sets: runtime data users pass on the command line.
        # keep_path=True preserves the HMM/ prefix -> package/res/HMM/*
        copy(self, "HMM/*", self.source_folder,
             os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
