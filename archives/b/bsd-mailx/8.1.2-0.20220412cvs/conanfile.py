#!/usr/bin/env python3
"""Conan recipe for bsd-mailx 8.1.2-0.20220412cvs (upstream Makefile build).

The upstream source uses OpenBSD bsd.prog.mk; our adaptation replaces it
with a GNU-make compatible Makefile (see patches/).  No external runtime
dependencies: the OpenBSD-specific pledge(2)/lockspool(1)/vis(3) pieces are
handled in the source adaptation without liblockfile/libbsd.

vis.c/vis.h are new source files (not present upstream) providing the BSD
vis(3) API that OHOS libc lacks; they are shipped via exports_sources and
copied into the source tree during build (not via patches/ so that
refresh-patch does not regenerate them as new-file patches).
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


class BsdMailxConan(ConanFile):
    name = "bsd-mailx"
    version = "8.1.2-0.20220412cvs"
    description = "BSD mailx: the traditional command line mail user agent (send/receive mail)."
    license = "BSD-3-Clause"
    homepage = "https://salsa.debian.org/debian/bsd-mailx"
    url = "https://salsa.debian.org/debian/bsd-mailx"
    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)
        # vis.c/vis.h are OHOS-specific additions (BSD vis(3) API not in
        # OHOS libc). Ship them with the recipe and copy into the source
        # tree at build time.
        copy(self, "vis.c", src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "vis.h", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("bsd-mailx requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)
        # Copy the OHOS-specific vis(3) implementation into the source tree.
        copy(self, "vis.c", src=self.export_sources_folder, dst=self.source_folder)
        copy(self, "vis.h", src=self.export_sources_folder, dst=self.source_folder)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        self.run('make -j1 CC="{}"'.format(cc))

    def package(self):
        self.run(
            "make install DESTDIR={}".format(self.package_folder)
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
