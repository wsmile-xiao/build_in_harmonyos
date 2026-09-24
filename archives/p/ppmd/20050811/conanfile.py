#!/usr/bin/env python3
"""Conan recipe for ppmd 20050811 — PPMd variant I file-to-file compressor.

ppmd is a self-contained C++ console tool (two translation units, no external
library dependencies). The upstream tarball ships a FreeBSD pmake-only Makefile
and i386-only code assumptions; the portability patches in conandata.yml make
it build and round-trip correctly on aarch64 (LP64) with clang 15. The patched
GNU Makefile drives the build, with compiler and flags supplied by Conan.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PpmdConan(ConanFile):
    name = "ppmd"
    version = "20050811"
    description = "Fast PPMd (prediction by partial matching) file-to-file compressor, variant I"
    license = "Public Domain"
    homepage = "https://packages.debian.org/unstable/utils/ppmd/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("compression", "ppm", "archiver", "cli")

    # ppmd ships a single executable and no libraries.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compiler from Conan conf, never from shell env vars.
        # tools.build:compiler_executables is a dict-valued conf; Conan 2's
        # conf.get() does not support ":cpp" subkey syntax, so fetch the whole
        # dict and index it (see $WORKSPACE_ROOT/framework overlay notes).
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = comp.get("cpp", "clang++")
        cxxflags = " ".join(self.conf.get("tools.build:cxxflags", default=[], check_type=list))

        # Upstream Makefile is FreeBSD pmake-only; patch 0005 rewrites it as a
        # plain GNU make Makefile. R9: one job on the shared device.
        # make runs with cwd=self.build_folder, so point it at the sources.
        self.run(
            f'make -C "{self.source_folder}" '
            f'CXX="{cxx}" CXXFLAGS="-O2 {cxxflags}" -j1'
        )

    def package(self):
        copy(
            self,
            "ppmd",
            os.path.join(self.source_folder),
            os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "read_me.txt",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # ppmd is a CLI tool: it ships no library, only bin/ppmd.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
