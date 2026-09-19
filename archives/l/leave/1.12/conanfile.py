#!/usr/bin/env python3
"""Conan recipe for leave 1.12 — the BSD "remind you when you have to leave"
command-line utility.

leave is part of the NetBSD/FreeBSD base systems (usr.bin/leave, original
4.4BSD code, BSD-3-Clause, Copyright (c) 1980, 1988, 1993 The Regents of the
University of California).  Upstream never published a stand-alone release, so
the recipe consumes the pristine upstream tarball distributed verbatim under
the ".orig" name (see conandata.yml and notes.md for the R39 provenance
reasoning).

Build-system adaptation
-----------------------
The shipped Makefile is a *BSD make* fragment:

    PROG=leave
    .include <bsd.prog.mk>

`bsd.prog.mk` is part of the BSD build framework and is not installed outside
a BSD source tree, so the Makefile cannot be used on OHOS/CI.  The only real
build unit is the single translation unit leave.c, which is compiled directly
with the Conan-provided C compiler (R33: the compiler and the cflags both come
from the Conan configuration, never from an ambient shell variable).

Platform adaptation (patch 0001, applied to a clean extraction)
---------------------------------------------------------------
* <sys/cdefs.h> on musl/OHOS does not define the NetBSD __COPYRIGHT/__RCSID
  macros; the patch adds portable #ifndef fallbacks.
* The BSD getprogname(3) interface is absent from OHOS musl libc (only
  __progname is exported); the patch adds a fallback that is compiled only on
  non-BSD platforms, keeping the BSD code paths untouched.
* `u_int` is a BSD <sys/types.h> spelling that musl exposes only behind
  feature-selection macros; the patch uses the portable `unsigned int`.

No `#ifdef __OHOS__` is introduced: these are ordinary portability fixes whose
effect on the BSD platforms is nil.

The executable links only against libc, so the R26 system-name-library rule
is satisfied trivially.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LeaveConan(ConanFile):
    name = "leave"
    version = "1.12"

    license = "BSD-3-Clause"
    homepage = "https://man.netbsd.org/leave.1"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    description = "Reminds you when you have to leave (BSD command-line utility)"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: never rely on an ambient $CC / $CFLAGS — take both from the
        # Conan configuration.  The ohos-aarch64 profile pins the OHOS clang
        # via tools.build:compiler_executables; any tools.build:cflags the
        # profile declares are forwarded explicitly to the compiler.
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        )
        cc = compiler_executables.get("c", "cc")
        cflags = self.conf.get("tools.build:cflags", default=[], check_type=list)

        source = os.path.join(self.source_folder, "leave.c")
        executable = os.path.join(self.build_folder, "leave")
        self.run(
            '"{}" {} -O2 -o "{}" "{}"'.format(
                cc, " ".join(cflags), executable, source
            )
        )

    def package(self):
        copy(
            self,
            "leave",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "leave.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        # Upstream ships no separate license file — the BSD-3-Clause notice is
        # the comment block at the top of leave.c, so that file is shipped as
        # the license text.
        copy(
            self,
            "leave.c",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        self.runenv_info.prepend_path(
            "PATH",
            os.path.join(self.package_folder, "bin"),
        )
