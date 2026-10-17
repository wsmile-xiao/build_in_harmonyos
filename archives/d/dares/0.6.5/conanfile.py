#!/usr/bin/env python3
"""Conan recipe — dares 0.6.5 (DAta REScue, ISO9660 file rescue, ncurses TUI).

dares (DAta REScue, c't Magazin) rescues files from damaged CD/DVD images
(ISO9660). Upstream builds via a hand-written recursive Makefile (no
configure, no install target). Only the ncurses frontend is built: the
top-level `all` target also pulls in the abandoned Qt3 frontend, which is
unavailable on OHOS — so this recipe invokes frontend/ncurses/Makefile
directly (see notes.md).

Dependencies (conan requires, static):
  - ncurses/6.6 — wide-character build; links -lncursesw (E033/E028)
  - file/5.48.1 — libmagic (static, R26); first -lmagic consumer in this repo

Upstream ships no test suite (verified against the full tarball file list:
no test sources, no check/test Makefile target); test_package provides a
self-built non-interactive smoke test. See test_package/MANIFEST.yml.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    copy, get, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.layout import basic_layout


class DaresConan(ConanFile):
    name = "dares"
    version = "0.6.5"
    description = "DAta REScue - saves files from damaged CDROMs/DVDs (ISO9660)"
    license = "GPL-2.0-or-later"
    homepage = "http://www.heise.de/ct/projekte/dares"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ncurses and libmagic are consumed as conan packages (both packaged
        # statically), not via cmd-pkgs: dares is the first in-repo libmagic
        # (-lmagic) consumer and libmagic is not part of the cmd-pkgs set.
        self.requires("ncurses/6.6")
        self.requires("file/5.48.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "dares is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Hand-written Makefile (patched so CC/CPPFLAGS/CFLAGS/LDFLAGS are
        # overridable and libraries are linked after the object files —
        # required for static archives).
        ncurses = self.dependencies["ncurses"]
        libmagic = self.dependencies["file"]
        ncurses_inc = os.path.join(ncurses.package_folder, "include")
        ncurses_lib = os.path.join(ncurses.package_folder, "lib")
        magic_inc = os.path.join(libmagic.package_folder, "include")
        magic_lib = os.path.join(libmagic.package_folder, "lib")

        cc = str(self.settings.compiler)
        # Wide-char ncurses (-lncursesw, E033/E028) + static libmagic.
        make_cmd = (
            "make -j1 "
            f'CC="{cc}" '
            f'CPPFLAGS="-I{ncurses_inc} -I{magic_inc}" '
            'CFLAGS="-O2 -Wall" '
            f'LDFLAGS="-L{ncurses_lib} -L{magic_lib} -lncursesw -lmagic"'
        )
        self.run(
            make_cmd,
            cwd=os.path.join(self.source_folder, "frontend", "ncurses"),
        )

    def package(self):
        # No upstream install target; copy the built binary manually.
        copy(
            self,
            "dares",
            src=os.path.join(self.source_folder, "frontend", "ncurses"),
            dst=os.path.join(self.package_folder, "bin"),
        )
        # Magic database decision (see notes.md): dares resolves "magic" /
        # "magic.mime" relative to the CWD first, then falls back to
        # libmagic's compiled-in default path — which is broken in the
        # redistributed prebuilt libmagic ("//share/misc/magic"). Upstream's
        # own magic files are file-3.x era and FAIL to load under libmagic
        # 5.48 (parse aborted, 0 files detected — verified empirically).
        # Ship libmagic 5.48.1's own compiled database instead and point the
        # libmagic fallback (MAGIC env var) at it, so classification works
        # from any CWD and stays version-matched to the linked libmagic.
        magic_mgc = os.path.join(
            self.dependencies["file"].package_folder, "share", "misc", "magic.mgc"
        )
        if os.path.isfile(magic_mgc):
            copy(self, "magic.mgc",
                 src=os.path.join(self.dependencies["file"].package_folder,
                                  "share", "misc"),
                 dst=os.path.join(self.package_folder, "share", "dares"))

    def package_info(self):
        # Standalone terminal binary, not a library.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # libmagic honours the MAGIC env var on its fallback load path
        # (magic_load(cookie, NULL)), so dares finds a working database
        # from any CWD even without a staged "magic" file next to it.
        magic_db = os.path.join(self.package_folder, "share", "dares", "magic.mgc")
        self.runenv_info.define_path("MAGIC", magic_db)
