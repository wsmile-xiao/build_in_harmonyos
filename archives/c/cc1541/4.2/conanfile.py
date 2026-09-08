#!/usr/bin/env python3
"""Conan recipe for cc1541 4.2 — Commodore 1541/1571 disk image creator.

Upstream builds with a plain Makefile (no configure step): `make all`
produces the cc1541 executable, and `make check` builds and runs the
official 135-case functional suite. The Makefile appends external flags via
`override CFLAGS := $(CC1541_CFLAGS) $(CFLAGS)`, so CFLAGS from the Conan
environment are kept after the upstream defaults.

Source note: the upstream Bitbucket workspace (PTV_Claus/cc1541) has been
deactivated by Bitbucket, so the authoritative official 4.2 artifact is the
author-published release zip on CSDb (release id 240041, linked from the
official documentation site acoustic-velocity.com/cc1541).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Cc1541Conan(ConanFile):
    name = "cc1541"
    version = "4.2"
    description = "Tool for creating Commodore 1541 floppy disk images in D64, G64, D71 or D81 format"
    license = "MIT"
    homepage = "https://bitbucket.org/PTV_Claus/cc1541"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32: OHOS must be accepted alongside Linux
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cc1541 requires a POSIX host (Linux or OHOS), got {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: the compiler comes from Conan conf, never from bare shell env
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: single-job build; upstream default target `all` builds the cc1541
        # binary. The man-page target needs a2x/asciidoc and stays disabled
        # (ENABLE_MAN unset) — it is an optional documentation feature.
        self.run(f"make all CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # Upstream's install rule shells out to coreutils `install`, which the
        # build host does not provide, so copy the single binary directly
        # (shutil-level copy keeps the executable bit set by make).
        copy(self, "cc1541", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
