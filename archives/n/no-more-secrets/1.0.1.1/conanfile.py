#!/usr/bin/env python3
"""Conan recipe — no-more-secrets 1.0.1.1 (Sneakers-style data decryption effect).

no-more-secrets ships two CLI tools, `nms` and `sneakers`, that recreate the
famous data-decryption effect from the 1992 movie "Sneakers".  The upstream
tarball is a plain GNU-Make project (no configure); two flavours are provided:
an ANSI/VT100 one with no dependencies and an ncurses one.  We build the
ncurses flavour (the one packaged by mainstream distros).

R37: 1.0.1 was already published for this project; this revision (.1) fixes the
runtime gap found on HarmonyOS PC (see notes.md for the full evidence):

  * R26: terminal tools must be statically linked — the recipe now depends on
    the OHOS-adapted ncurses/6.4 recipe (static-only, built --without-shared,
    ships the terminfo database), instead of ncurses/6.6.
  * terminfo database: HarmonyOS PC's /usr/share/terminfo is incomplete, so an
    ncurses application aborts at startup ("Error opening terminal").  The
    package now ships share/terminfo (copied from the ncurses dependency) and
    package_info() defines TERMINFO/TERMINFO_DIRS for consumers.
  * consumer test: 1.0.1 only ran `nms -v`, which returns before ncurses is
    initialised and therefore never exercised the effect.  1.0.1.1 runs both
    tools under a pseudo-terminal (KB: TUI pty harness) and asserts the effect
    output and the bundled terminfo are what make them work.

OHOS notes:
  * The Makefile links the -ncurses targets with only `$(CC) $(CFLAGS)`, so the
    cross toolchain cannot pass -L<dep libdir>.  Patch 0001 adds $(LDFLAGS) to
    the two link lines (generic Makefile improvement, no platform macro).
  * `install` from GNU coreutils is not available in the OHOS build sandbox;
    package() copies the produced binaries and man pages directly instead of
    running `make install`.
  * nms initialises ncurses through initscr(); when stdin is not a tty it
    first reopens /dev/tty (nmstermio_ncurses.c), like ne 3.3.4 — tests must
    therefore run under a pty.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class NoMoreSecretsConan(ConanFile):
    name = "no-more-secrets"
    version = "1.0.1.1"
    description = (
        "Command line tool that recreates the famous data decryption "
        "effect seen in the 1992 movie Sneakers"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/bartobri/no-more-secrets"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("terminal", "ncurses", "cli", "sneakers")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R4/R26: ncurses/6.4 is the OHOS-adapted, static-only recipe
        # (--without-shared) and it ships share/terminfo, which the effect
        # needs at runtime on HarmonyOS PC (ne/boxes/astroterm use the same).
        self.requires("ncurses/6.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS").
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"no-more-secrets is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        # Upstream uses a plain in-source Makefile (no VPATH) -> force
        # in-source build so `make` sees its own sources/objects.
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler must come from the Conan toolchain, never from an
        # undefined shell var (empty on release workers).
        comp = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = comp.get("c") or os.environ.get("CC") or "clang"
        ncurses_pkg = self.dependencies["ncurses"].package_folder
        nc_inc = os.path.join(ncurses_pkg, "include")
        nc_lib = os.path.join(ncurses_pkg, "lib")
        self.run(
            f"make -j1 CC={cc} "
            f"CFLAGS=\"-fPIC -O2 -I{nc_inc}\" "
            f"LDFLAGS=\"-L{nc_lib}\" "
            "all-ncurses"
        )

    def package(self):
        src_bin = os.path.join(self.build_folder, "bin")
        copy(self, "nms", src=src_bin,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "sneakers", src=src_bin,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "nms.6", src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man6"))
        copy(self, "sneakers.6", src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man6"))
        copy(self, "LICENSE", src=self.build_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # terminfo database from the ncurses dependency: the effect needs it at
        # runtime and HarmonyOS PC's /usr/share/terminfo is incomplete, so the
        # package carries its own copy (KB: terminfo-database-bundle).
        tinfo_src = os.path.join(
            self.dependencies["ncurses"].package_folder, "share", "terminfo"
        )
        if not os.path.isdir(tinfo_src):
            raise ConanInvalidConfiguration(
                "ncurses dependency does not ship share/terminfo: " + tinfo_src
            )
        copy(self, "*", src=tinfo_src,
             dst=os.path.join(self.package_folder, "share", "terminfo"))

    def package_info(self):
        # Pure command-line tool: no libraries or headers to expose.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        # TERMINFO takes precedence over /usr/share/terminfo; TERMINFO_DIRS is
        # the fallback search list for ncurses >= 6.
        terminfo = os.path.join(self.package_folder, "share", "terminfo")
        self.runenv_info.define_path("TERMINFO", terminfo)
        self.runenv_info.define_path("TERMINFO_DIRS", terminfo)
