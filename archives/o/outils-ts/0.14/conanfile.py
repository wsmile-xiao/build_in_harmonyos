#!/usr/bin/env python3
"""Conan recipe — outils-ts 0.14

`outils-ts` packages the `ts` utility taken from the outils project
(https://github.com/leahneukirchen/outils) — "a port of some non-standard
OpenBSD tools to Linux".  ts(1) is "timestamp input": it prepends a
timestamp to every line read from standard input (see share/man/man1/ts.1).

Upstream layout / build system
------------------------------
Pure hand-written GNU Makefile project (no configure/cmake/autotools; the
per-tool OpenBSD `bsd.prog.mk` style Makefiles do not take part in the
top-level build).  This package builds only the `src/usr.bin/ts/ts` target,
whose upstream link closure is

    src/usr.bin/ts/ts.o src/liboutils/strlcpy.o src/liboutils/pledge.o

OHOS notes
----------
* OHOS libc (musl) has no reallocarray(3): the make-time link fails with
  "ld.lld: error: undefined symbol: reallocarray".  The in-tree compat
  object src/liboutils/reallocarray.o must be added to the closure, which
  is exactly what patches/0001-Makefile.patch does (see notes.md).
* No third-party dependencies at all: ts links only libc (and the in-tree
  liboutils objects).  pledge(3) is an in-tree no-op stub on Linux/OHOS.
* The upstream `install` target requires coreutils install(1) and writes
  into the baked-in system PREFIX; packaging uses Conan copy() instead.
* CI L0p requires all four settings (os, compiler, build_type, arch); R33
  obtains the compiler from Conan conf rather than the shell environment.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OutilsTsConan(ConanFile):
    name = "outils-ts"
    version = "0.14"
    description = ("ts(1) - timestamp input, taken from the outils OpenBSD port "
                   "collection (prepends a timestamp to each line of stdin)")
    license = "0BSD"
    homepage = "https://github.com/leahneukirchen/outils"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # This is an executable, NOT a library.
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

        # R33: take the compiler from Conan conf, never from the ${CC} shell
        # variable (the profile sets tools.build:compiler_executables as a dict).
        comp_execs = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        # R9: -j1.  Build only the ts target — this package ships ts alone.
        self.run(f'make CC="{cc}" -j1 src/usr.bin/ts/ts',
                 cwd=self.source_folder)

    def package(self):
        # OHOS has no coreutils install(1) and the upstream install target
        # targets the system PREFIX, so copy the artifacts directly.
        copy(self, "ts",
             os.path.join(self.source_folder, "src", "usr.bin", "ts"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "ts.1",
             os.path.join(self.source_folder, "src", "usr.bin", "ts"),
             os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Application package: only bindirs, no libs.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
