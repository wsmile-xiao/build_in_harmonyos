#!/usr/bin/env python3
"""Conan recipe for ries 2018.08.05 — RIES equation finder (single-file C CLI).

RIES finds algebraic equations whose solution equals a given number.
Build: upstream GNUmakefile, one translation unit (`ries.c`), one link flag
(`LDLIBS = -lm`).  No configure script, no external dependencies.

Packaging note: upstream's `install` target shells out to the host `install(1)`
program, which the OHOS worker does not provide, so the recipe places the
binary and the man page with Conan's own copy() instead of `make install`.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RiesConan(ConanFile):
    name = "ries"
    version = "2018.08.05"
    description = ("RIES — finds algebraic equations, given their solution "
                   "(single-file C command-line equation finder)")
    license = "GPL-3.0-or-later"
    homepage = "https://mrob.com/pub/ries/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("math", "equation-solver", "cli", "terminal")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream needs nothing but libm, which is part of the OHOS libc.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler comes from the Conan toolchain conf, never from bare
        # shell variables (${CC} is empty on CI workers).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = (compilers or {}).get("c") or "clang"

        # The upstream GNUmakefile keeps CFLAGS as `?=-g -O2
        # -fstack-protector-strong -D_FORTIFY_SOURCE=2`; those defaults build
        # clean with the OHOS clang 15, so they are left untouched (R1 — no
        # gratuitous flags).  R9: -j1.
        self.run(f"make -f GNUmakefile CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # Upstream `make install` = `install -m 0755 ries $(DESTDIR)$(BINDIR)`;
        # install(1) is absent on the OHOS worker, so place the artifacts here.
        copy(self, "ries", self.source_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "ries.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
