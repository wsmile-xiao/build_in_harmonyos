#!/usr/bin/env python3
"""Conan recipe for mmc-utils 1.0 (upstream Makefile build)."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MmcUtilsConan(ConanFile):
    name = "mmc-utils"
    version = "1.0"
    description = "Userspace tools for MMC/SD/SDIO devices (eMMC and SD card utilities)."
    license = "GPL-2.0-only"
    homepage = "https://git.kernel.org/pub/scm/utils/mmc/mmc-utils.git"
    url = "https://git.kernel.org/pub/scm/utils/mmc/mmc-utils.git"
    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # The upstream Makefile is in-source and has no out-of-tree support
        # (objects and `mmc` are emitted next to the sources) — build in place.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("mmc-utils requires a Linux/OHOS host")
        apply_conandata_patches(self)
        # R33: obtain the compiler from Conan conf — ${CC} is empty on CI workers.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # Two upstream Makefile defaults are unusable on OHOS:
        #   * `C ?= 1` runs `sparse` on every object — sparse is absent, so the
        #     build dies with Error 127. `C=0` disables the checker.
        #   * `GIT_VERSION := $(shell git describe ...)` yields an empty string in
        #     a source tarball, leaving the -DVERSION macro blank; pass the
        #     release tag explicitly.
        # R9: keep -j1 for the Makefile.
        self.run(
            "make -j1 CC={} C=0 GIT_VERSION={}".format(cc, self.version)
        )

    def package(self):
        # Upstream `make install` hardcodes `INSTALL = install`, which does not
        # exist on OHOS, and `mandir = /usr/share/man`. The install set is tiny
        # (the `mmc` binary + mmc.1), so copy the artifacts directly instead of
        # factoring in an `install` shim.
        copy(
            self,
            "mmc",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "mmc.1",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
