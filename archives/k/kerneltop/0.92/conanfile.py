#!/usr/bin/env python3
"""Conan recipe for kerneltop 0.92 - kernel function usage "top" front-end.

kerneltop reads the kernel profiling histogram (/proc/profile) plus a
System.map and prints the hottest kernel functions in a top-like screen.
It is derived from util-linux' readprofile.c and ships as three files only
(kerneltop.c, makefile, vidsupport.h) built by a raw POSIX makefile - no
configure, no cmake, no meson, no external library dependency.

Because the result is an executable and not a library:
  - package_type = "application"
  - no shared/static options
  - requirements() is empty
  - package_info() declares bindirs only (no libs)

Cross-compilation notes (all three points are E392 raw-makefile traps):
  * the makefile hard-codes CC=gcc, so CC is overridden from the Conan
    profile's tools.build:compiler_executables dict - R33 forbids reading
    the bare ${CC} shell variable, which is empty on a release worker;
  * the file is named "makefile" (all lower case), which GNU make
    auto-discovers, and it lives in source_folder, so make must run with
    cwd=source_folder;
  * the makefile has no install target, so package() copies the produced
    binary itself (the OHOS platform has no `install` coreutils command).
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


class KerneltopConan(ConanFile):
    name = "kerneltop"
    version = "0.92"
    description = (
        "Shows kernel function usage in a top-like full-screen layout by "
        "reading /proc/profile together with a System.map symbol table"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.infradead.org/~rdunlap/src/"
    url = ""  # filled by CI
    author = "Randy Dunlap <rdunlap@infradead.org>"
    topics = ("kernel", "profiling", "monitor", "cli", "system")

    # Executable, not a library.
    package_type = "application"

    # CI L0p requires all four settings.
    settings = "os", "compiler", "build_type", "arch"

    # No options (an application has no shared/static axis) and no
    # dependencies: the tarball is 1 .c file + 1 private header.

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # kerneltop links against nothing beyond libc; its Build-Depends in
        # any downstream packaging is only the debhelper tooling itself.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Pass an explicit *.tar.gz filename: the URL tail does carry the
        # extension here, but naming it removes any dependence on Conan's
        # decoder auto-selection (E392 trap 1).
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="kerneltop-0.92.tar.gz")

    def build(self):
        apply_conandata_patches(self)

        # R33: take the cross compiler from the Conan profile, never from the
        # ${CC} shell variable.  The OHOS profile stores
        # tools.build:compiler_executables as a dict, so read the whole dict
        # with check_type=dict and then pick "c" (E392 trap 2, forbid_2).
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = comp_execs.get("c") or "clang"

        # The upstream makefile is:
        #     CC=gcc
        #     ifeq "$(DEBUG)" "y"
        #     CCFLAGS=-g $(CFLAGS)
        #     else
        #     CCFLAGS=-s $(CFLAGS)
        #     endif
        #     kerneltop: kerneltop.c
        #             $(CC) -c -O2 $(CCFLAGS) -I. -Wall -Wstrict-prototypes ...
        #             $(CC) $(CCFLAGS) kerneltop.o -o kerneltop
        #
        # Neither CC nor CCFLAGS carries an `override` directive, so a make
        # command-line assignment wins over the in-file one.  CCFLAGS= clears
        # the else-branch `-s`, i.e. it removes the link-time strip while
        # leaving -O2 -Wall -Wstrict-prototypes untouched.  This is defensive,
        # not a workaround for an observed failure: on this machine the
        # default `-s` build was measured to exec fine, while a *post-link*
        # `llvm-strip` on the very same ELF made it unrunnable (rc=126),
        # because the OHOS kernel validates the .codesign segment that the
        # SDK signs at link time.  Keeping every post-link ELF rewrite out of
        # the picture is the cheap way to stay on the right side of that.
        #
        # E392 trap 3: the raw makefile lives in source_folder, so pass cwd.
        # R9: -j1.
        self.run(f'make CC="{cc}" CCFLAGS= -j1', cwd=self.source_folder)

    def package(self):
        # No install target upstream and no `install` command on OHOS: copy
        # the produced binary into the package bin/ ourselves.  The upstream
        # tarball ships no man page or doc file, so there is nothing else to
        # install.  copy() only, never strip/objcopy: see build().
        copy(self, "kerneltop",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)

    def package_info(self):
        # Executable package: expose bin/ on PATH, no libraries to link.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
