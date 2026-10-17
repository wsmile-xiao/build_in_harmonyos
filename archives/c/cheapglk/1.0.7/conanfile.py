#!/usr/bin/env python3
"""Conan recipe for CheapGlk 1.0.7 — an extremely minimal Glk library.

Upstream: https://github.com/erkyrath/cheapglk
License:  MIT
Build:    plain Unix Makefile (no configure, no install target)

The Makefile produces libcheapglk.a and a Make.cheapglk snippet. There is
no install rule, so package() copies the library and public headers into
the Conan package layout by hand. Pure ANSI C, zero dependencies.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CheapGlkConan(ConanFile):
    name = "cheapglk"
    version = "1.0.7"
    description = "CheapGlk — an extremely minimal Glk implementation for Unix"
    license = "MIT"
    homepage = "https://github.com/erkyrath/cheapglk"
    url = ""  # CI fills this

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_tools(self):
        """Resolve cc / ar / ranlib from profile conf (R33: no env guessing).

        CC stays a bare path (may contain spaces). Target/sysroot flags are
        passed via CFLAGS: make command-line assignments override the
        Makefile's plain `=` definitions, so this works without patching
        CheapGlk's Makefile.
        """
        execs = self.conf.get("tools.build:compiler_executables",
                              default={}, check_type=dict)
        cc = execs.get("c") or "clang"
        ar = execs.get("ar") or "llvm-ar"
        ranlib = execs.get("ranlib") or "llvm-ranlib"
        cflags = []
        for flag in self.conf.get("tools.build:cflags",
                                  default=[], check_type=list):
            if flag.startswith("--target=") or flag.startswith("--sysroot"):
                cflags.append(flag)
        sysroot = self.conf.get("tools.build:sysroot", default="",
                                check_type=str)
        if sysroot and not any(f.startswith("--sysroot") for f in cflags):
            cflags.append(f"--sysroot={sysroot}")
        if self.settings.build_type == "Release":
            cflags.append("-O2")
        elif self.settings.build_type == "Debug":
            cflags.append("-g")
        return cc, ar, ranlib, " ".join(cflags)

    def build(self):
        apply_conandata_patches(self)
        cc, ar, ranlib, cflags = self._compiler_tools()
        # Makefile uses bare `ar r` + `ranlib`; the OHOS SDK exposes these as
        # llvm-ar / llvm-ranlib (mapped into PATH via the conanrun env).
        # make command-line CC/CFLAGS override the Makefile's `=` definitions.
        self.run(
            f'make CC="{cc}" AR="{ar}" RANLIB="{ranlib}" CFLAGS="{cflags}" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "libcheapglk.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "glk.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "glkstart.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "cheapglk.h", self.source_folder,
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["cheapglk"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "cheapglk")
        self.cpp_info.set_property("cmake_target_name", "cheapglk::cheapglk")