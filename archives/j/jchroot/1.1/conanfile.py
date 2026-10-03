#!/usr/bin/env python3
"""Conan recipe for jchroot 1.1 (upstream Makefile build)."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class JchrootConan(ConanFile):
    name = "jchroot"
    version = "1.1"
    description = (
        "Chroot with more isolation: new mount/PID/IPC/UTS namespaces plus pivot_root."
    )
    license = "ISC"
    homepage = "https://github.com/vincentbernat/jchroot"
    url = "https://github.com/vincentbernat/jchroot"
    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # The upstream Makefile is in-source and has no out-of-tree support
        # (objects and `jchroot` are emitted next to the sources) — build in place.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("jchroot requires a Linux/OHOS host")
        apply_conandata_patches(self)
        # R33: obtain the compiler from Conan conf — ${CC} is empty on CI workers.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # Upstream sets `CFLAGS = -Werror -Wall -ansi -g -O2` by hard assignment
        # (not `?=`), which clang 15 satisfies without warnings; no override is
        # needed. R9: keep -j1 for the Makefile.
        self.run("make -j1 CC={}".format(cc))

    def package(self):
        # The upstream Makefile has no `install` target at all, so the artifacts
        # are copied directly: the single `jchroot` binary, its man page and the
        # ISC license.
        copy(
            self,
            "jchroot",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "jchroot.8",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man8"),
        )
        copy(
            self,
            "LICENSE",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
