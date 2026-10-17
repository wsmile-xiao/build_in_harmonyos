#!/usr/bin/env python3
"""Conan recipe for mtm 1.2.1 (upstream custom Makefile build).

mtm is a small terminal multiplexer: one C file (mtm.c) plus a VT parser
(vtparser.c), linked against ncursesw.  Upstream build is a single custom
Makefile with no configure step (E097).

Adaptation notes:
- CC/LIBPATH use `?=` so they can be overridden on the make command line;
  the compiler comes from tools.build:compiler_executables (profile conf),
  not from shell env vars (R33).
- The upstream `mtm` target runs `strip mtm` unconditionally.  On OHOS the
  binary-signing toolchain rejects stripped packed binaries with EPERM
  (E077), so build the object files and link `mtm` directly instead of
  running the default target.
- The upstream rule regenerates config.h with `cp -i config.def.h
  config.h`, which blocks interactively when config.h exists; we create
  config.h ourselves and never invoke that rule (E214 family).
- forkpty() lives in libc on OHOS musl (libutil is merged; the sysroot
  ships only an empty stub libutil.a), so upstream LIBS `-lutil` is
  dropped.  ncurses provides the rest via -lncursesw.
- ncursesw on musl needs _DEFAULT_SOURCE for proper wchar/cchar support
  (E033 family).

Knowledge refs: E097, E077, E214, E010, E033.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class MtmConan(ConanFile):
    name = "mtm"
    version = "1.2.1"
    description = "Micro Terminal Multiplexer - simple, modern terminal multiplexer."
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/deadpixi/mtm"
    url = "https://github.com/deadpixi/mtm"
    topics = ("terminal", "multiplexer", "tui", "curses")
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.output.error("mtm requires a POSIX host (Linux or OHOS)")
            raise Exception("unsupported os: %s" % self.settings.os)

        # R33: compiler comes from Conan conf (profile), not env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        if os.path.isfile(cc):
            cc_bin = cc
        else:
            cc_bin = shutil.which(os.path.basename(cc)) or cc

        ncurses = self.dependencies["ncurses"]
        ninfo = ncurses.cpp_info.aggregated_components()
        inc = ninfo.includedirs[0]
        libdir = ninfo.libdirs[0]
        libs = " ".join("-l" + l for l in ninfo.libs)
        ldflags = os.environ.get("LDFLAGS", "").split()

        # E097: `make mtm` would run `strip mtm` (E077) and `cp -i` (E214).
        # Generate config.h non-interactively ourselves, then run the exact
        # compile+link command from the Makefile's mtm rule, minus strip
        # and -lutil (libutil is merged into libc on OHOS musl).
        if not os.path.exists(os.path.join(self.source_folder, "config.h")):
            shutil.copyfile(
                os.path.join(self.source_folder, "config.def.h"),
                os.path.join(self.source_folder, "config.h"),
            )
        features = ("-D_POSIX_C_SOURCE=200809L -D_XOPEN_SOURCE=600 "
                    "-D_XOPEN_SOURCE_EXTENDED")
        # config.def.h includes <ncursesw/curses.h> on Linux, but the conan
        # ncurses package installs headers flat into include/; select the
        # flat <curses.h> via the NCURSESW_INCLUDE_H escape hatch.  The
        # macro value must be shell-quoted (it contains < >).
        cflags = (f"-std=c99 -Wall -Wextra -pedantic -Os -I{inc} {features} "
                  "-DNCURSESW_INCLUDE_H='<curses.h>'")
        self.run(
            "{cc} {cflags} -o mtm vtparser.c mtm.c pair.c "
            "-L'{libdir}' {libs} {ldflags}".format(
                cc=cc_bin,
                cflags=cflags,
                libdir=libdir,
                libs=libs,
                ldflags=" ".join(ldflags),
            ),
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "mtm", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "mtm.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "mtm.ti", self.source_folder, os.path.join(self.package_folder, "share", "terminfo", "src"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
