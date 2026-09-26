#!/usr/bin/env python3
"""Conan recipe for recoverdm 0.20 — recover data from disks/images with bad sectors.

Upstream: https://www.vanheusden.com/recoverdm (folkert@vanheusden.com, 2003-2004).
Distribution tarball: Debian pool pristine upstream source
`recoverdm_0.20.orig.tar.gz` (uncompressed upstream release, root dir
`recoverdm-0.20/`, strip_root=True).

Build system: bare Makefile, no configure script, zero third-party dependencies
(only system libc; 6 .c + 5 .h = 1486 lines).

Build outputs (see upstream Makefile):
  - recoverdm   (sector-by-sector recovery of a broken disk/image)
  - mergebad    (merge several partial images read from the same medium)

Adaptation notes (full evidence in notes.md):
  * The Makefile never assigns CC, so GNU make's built-in default `cc` is used.
    OHOS has no `cc` alias -> `make: cc: No such file or directory`
    (Error 127).  Fixed without patching by overriding CC on the make command
    line from the Conan conf (`tools.build:compiler_executables`, R33).
  * Upstream `CFLAGS` is a plain `=` assignment that embeds
    `-DVERSION=\\"$(VERSION)\\"`; overriding CFLAGS from the command line would
    drop the macro and break compilation.  Therefore CFLAGS is deliberately
    **not** overridden (R1 minimal-parameter rule).
  * The `install` target hard-codes `cp recoverdm mergebad /usr/local/bin`
    (no PREFIX/DESTDIR hook), so `make install` is never called; package()
    copies the two binaries into the Conan package folder instead.
  * `recoverdm.1` in the 0.20 orig tarball is a 0-byte file, so no man page is
    shipped.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class RecoverdmConan(ConanFile):
    name = "recoverdm"
    version = "0.20"
    description = (
        "Recover data from broken disks, CD/DVDs and disk images with bad "
        "sectors (includes the mergebad multi-image merger)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.vanheusden.com/recoverdm"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Zero third-party dependencies: plain libc only (preflight_check.sh
        # reports no dependency declarations).
        pass

    # R32: OHOS platform compatibility (`in`, not `==`)
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"recoverdm supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        # Upstream builds in-source (bare Makefile, no separate build dir).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        # R33: never read the compiler from bare shell env vars (${CC} is empty
        # on CI workers); take it from the Conan conf.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return (compilers or {}).get("c") or "clang"

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        # R9: -j1, never -j$(nproc).
        # Only CC is overridden: upstream CFLAGS carries -DVERSION and must
        # survive untouched (overriding it on the command line replaces the
        # whole assignment, see notes.md "CFLAGS 危险面" evidence).
        self.run(f'make -j1 CC="{cc}"', cwd=self.source_folder)

    def package(self):
        pkg_bin = os.path.join(self.package_folder, "bin")
        # Upstream `install` target writes to a hard-coded /usr/local/bin, so
        # the two freshly built binaries are installed by the recipe itself.
        # (No keep_permissions kwarg: the OHOS conan 2.29.1 copy() rejects it —
        #  measured 2026-09-25, G2 failed with
        #  "TypeError: copy() got an unexpected keyword argument".)
        copy(self, "recoverdm", self.source_folder, pkg_bin)
        copy(self, "mergebad", self.source_folder, pkg_bin)
        copy(
            self,
            "license.txt",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Command-line tools, no libraries / headers.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
