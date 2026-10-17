#!/usr/bin/env python3
"""Conan recipe — crack 5.0a.

Crack v5.0a is the classic Unix password cracker (Alec Muffett, 1991-1996).
The 1996 sources ship K&R-style C and a hand-rolled Makefile hierarchy with
no configure script: `Crack -makeonly` drives `src/lib` + `src/util` builds.
This recipe builds the same two stages directly with make, using the
`stdlib-cracker` backend (libc crypt) which needs no external crypt library.
It also builds the in-tree `src/libdes` backend to run the only registered
upstream test (`make test` -> ./destest, the DES self-test program).

K&R compatibility: clang 15 rejects K&R implicit conversions as errors in
newer C dialects; passing `-std=gnu89 -Wno-int-conversion` restores the
legacy semantics the 1996 code expects.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, mkdir
from conan.tools.layout import basic_layout


class CrackConan(ConanFile):
    name = "crack"
    version = "5.0a"
    description = "Crack v5.0a - the classic Unix password cracker by Alec Muffett"
    license = "Crack v5.0 LICENCE (freely distributable)"
    homepage = "https://packages.debian.org/sid/crack"
    url = "https://deb.debian.org/debian/pool/main/c/crack/crack_5.0a.orig.tar.gz"

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

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # Platform feature macros as documented in the upstream `Crack` driver
        c5flags = (
            "-DUSE_STRING_H -DUSE_STDLIB_H -DUSE_SIGNAL_H "
            "-DUSE_SYS_TYPES_H -DUSE_UNISTD_H -DUSE_PWD_H"
        )
        # K&R era code: gnu89 keeps implicit int/old-style definitions legal;
        # -Wno-int-conversion downgrades the K&R varargs int/pointer mixing
        # (cracker.c Logger) that modern clang treats as a hard error.
        xcflags = f"-std=gnu89 -Wno-int-conversion -O2 {c5flags}"
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        # Output dir must pre-exist: 'ar rv' fails on missing paths.
        mkdir(self, os.path.join(self.source_folder, "run", "bin"))

        # Stage 1: src/lib -> run/bin/libc5.a
        self.run(
            f'make -C src/lib "XDIR=../../run/bin" "XCFLAGS={xcflags}" "XCC={cc}"',
            cwd=self.source_folder,
        )
        # Stage 2: src/util -> dictfilt/kickdict + stdlib-cracker (cracker)
        self.run(
            f'make -C src/util "XDIR=../../run/bin" "XCFLAGS={xcflags}" '
            f'"XCC={cc}" "../../run/bin/stdlib-cracker" '
            f'"../../run/bin/dictfilt" "../../run/bin/kickdict"',
            cwd=self.source_folder,
        )
        # Stage 3: dawg — compiled directly instead of via the upstream
        # Makefile rule, because that rule ends with 'ln dawg xdawg' (a
        # hard link) and HMDFS forbids hard links. dawg/xdawg differ only
        # by argv[0]; a byte-identical copy behaves the same.
        runbin = os.path.join(self.source_folder, "run", "bin")
        self.run(
            f'"{cc}" {xcflags} -Isrc/lib -o run/bin/dawg src/util/dawg.c '
            f'run/bin/libc5.a',
            cwd=self.source_folder,
        )
        shutil.copy2(os.path.join(runbin, "dawg"), os.path.join(runbin, "xdawg"))

        # Stage 4: src/libdes — the upstream tree ships Eric Young's libdes
        # (an alternative crypt backend). Its Makefile carries the ONLY
        # registered upstream test target (`make test` -> ./destest, the
        # DES algorithm self-test program), so we build libdes and destest
        # to run that upstream test on the target. TERMIOS replaces the
        # legacy TERMIO (termio.h is not provided by musl).
        # Note: the delivered cracker still uses the stdlib-cracker backend
        # (libc crypt(3)); libdes is built solely to exercise upstream tests.
        des_cflags = "-O2 -std=gnu89 -Wno-int-conversion -Wno-implicit-function-declaration -DRAND -DTERMIOS"
        self.run(
            f'make -C src/libdes "CC={cc}" "CFLAGS={des_cflags}" destest',
            cwd=self.source_folder,
        )
        # Upstream test: src/libdes `make test` == ./destest (exit 0 on pass)
        self.run(
            "./destest",
            cwd=os.path.join(self.source_folder, "src", "libdes"),
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        mkdir(self, bindir)
        for tool in ("cracker", "dawg", "xdawg", "dictfilt", "kickdict"):
            copy(self, tool, src=os.path.join(self.source_folder, "run", "bin"),
                 dst=bindir, keep_path=False)
        copy(self, "LICENCE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
