#!/usr/bin/env python3
"""Conan recipe -- sma 1.4 (SMA - Sendmail log analyser).

Pure-C, single binary, raw Makefile project (no configure / CMake / Meson).

Facts measured on the upstream tree (details in notes.md):
  * The link rule is `$(CC) $(CFLAGS) -o sma $(OBJS)` with
    `CFLAGS = -Wall -O -DUSE_REGEXP`, and there is not a single `-l` flag in
    any Makefile in the tarball => this recipe has NO Conan requirements,
    libc only.
  * The BSD regex sources kept under regex/ are compiled only by
    Makefile.w32 / Makefile.msvcp.  sma.h includes the *system* <regex.h> on
    every non-Windows platform, so OHOS uses the C library's regcomp/regexec
    and regex/ is dead weight here.
  * Upstream hardcodes `CC = gcc` (the OHOS image ships clang) and bakes a
    shared system prefix into BINDIR/MANDIR => we override CC on the command
    line and never run `make install`; package() copies into the private
    package folder instead.  install(1) itself is not usable on this host
    (/bin/install not accessible, `install` absent from PATH), which also
    rules out upstream's `./install-sh` route.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SmaConan(ConanFile):
    name = "sma"
    version = "1.4"
    description = ("SMA - Sendmail log analyser: reads sendmail syslog files and "
                   "prints envelope/relay traffic reports in ascii, html or clog format")
    license = "BSD-2-Clause"
    homepage = "http://www.klake.org/sma/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Zero link-time dependencies: the upstream Makefile passes no -l flag
        # and the code needs nothing beyond libc (see module docstring).
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: only ever built/verified for the OHOS (and generic Linux) targets.
        if self.settings.os not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # conandata.yml declares one portability patch for 1.4 (the globals
        # extern conversion, see patches/ and notes.md section 2); the
        # export side is handled by export_conandata_patches() above.
        apply_conandata_patches(self)
        # R33: resolve the compiler from Conan conf, never from shell ${CC}.
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp.get("c") or comp.get("cc") or "clang"
        # Upstream Makefile hardcodes gcc and a bare CFLAGS line.  The tree puts
        # 93 file-scope globals (pname / tval / curr / tp / aflag .. wflag) in
        # sma.h as tentative definitions, i.e. one definition per translation
        # unit, which only links while the toolchain still defaults to the
        # legacy common-tentative-symbol mode.  OHOS clang-15 defaults to
        # -fno-common, so the first link fails (measured on B:
        # ld.lld "error: duplicate symbol: curr" + ": wflag",
        # make rc=2).  E491 explicitly forbids that global-compat flag route
        # (knowledge/graph/E491.kv:33 pattern, :34 reason, :35 consequence) and
        # its priority-1 recommendation (:21) is to "replace tentative
        # definitions with extern declarations plus one definition"; the 0001
        # patch does exactly that: sma.h wraps every such declaration in SMA_G
        # (extern by default, empty in the one TU that defines
        # SMA_GLOBALS_DEFINE before including sma.h, i.e. sma.c).  Proof of one
        # definition: nm --defined-only -g over all 8 objects lists each of the
        # 93 names exactly once and all of them in sma.o.  Merging the
        # tentative symbols behind that banned flag would have yielded the same
        # object layout as this patch, so behaviour is unchanged.
        # -DUSE_REGEXP is carried over explicitly: overriding
        # CFLAGS wholesale would silently disable the regex filter path.
        cflags = "-Wall -O -DUSE_REGEXP"
        self.run('make -j1 CC="' + cc + '" CFLAGS="' + cflags + '"',
                 cwd=self.source_folder)

    def package(self):
        copy(self, "sma", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "sma.8", src=os.path.join(self.source_folder, "docs"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        for doc in ("README", "HISTORY", "BUGS", "TODO", "sma.conf"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "doc", "sma"))
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Command-line tool, not a library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")

