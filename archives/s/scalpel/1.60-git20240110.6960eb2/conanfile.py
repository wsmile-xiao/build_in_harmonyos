#!/usr/bin/env python3
"""Conan recipe for scalpel 1.60-git20240110.6960eb2 — file-carving tool (raw Makefile).

Upstream snapshot: nolaforensix/scalpel-1.60 commit 6960eb2 (2024-01-10).
Build: plain GNU Make, no configure script. `make linux` adds -D__LINUX via a
target-specific `CC +=`, which GNU make silently drops when CC is overridden on
the command line — so -D__LINUX is injected here explicitly. Produces the
`scalpel` executable only (application package, no library).
Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ScalpelConan(ConanFile):
    name = "scalpel"
    version = "1.60-git20240110.6960eb2"
    description = "Scalpel 1.60 — fast header/footer-based file carver (rewrite of Foremost 0.69)"
    license = "GPL-2.0-or-later"  # LICENSE + gpl.txt; sources state "or (at your option) any later version"
    homepage = "https://github.com/nolaforensix/scalpel-1.60"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Self-contained snapshot: only libc/libm from the target sysroot.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get compiler from Conan conf, never from bare shell env vars.
        # [framework overlay note] tools.build:compiler_executables is a dict-valued
        # conf; Conan 2.29.1 conf.get() does not support ":c" subkey syntax.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # scalpel's Makefile sets -D__LINUX via a *target-specific* `CC += -D__LINUX`
        # (target `linux`). GNU make ignores that append for command-line variables,
        # so passing CC=<clang> alone would drop the platform define and fail in
        # helpers.c (basename() implicitly declared). Inject it here explicitly;
        # the duplicate -D__LINUX from the target-specific append is harmless.
        # R9: always -j1, never -j$(nproc).
        self.run(f'make linux -j1 CC="{cc} -D__LINUX -O2"', cwd=self.source_folder)

    def package(self):
        # Upstream has no install rule; copy the artifacts explicitly.
        copy(self, "scalpel", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Default carving configuration shipped next to the binary so the tool is
        # usable in place (upstream keeps it in the repo root; Debian installs it
        # to /etc/scalpel/, which a Conan package cannot assume).
        copy(self, "scalpel.conf", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "scalpel.1", self.source_folder, os.path.join(self.package_folder, "res"))
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "gpl.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
