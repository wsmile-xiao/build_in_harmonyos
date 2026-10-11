#!/usr/bin/env python3
"""Conan recipe for SweeD 3.2.1 - likelihood-based selective sweep detector.

Upstream ships a set of hand-written GNU makefiles (Makefile.gcc,
Makefile.PTHREADS.gcc, Makefile_MPFR.*.gcc).  This recipe uses the sequential
Makefile.gcc, which compiles the six SweeD*.c translation units and links -lm.
There are no third-party dependencies (the MPFR variant is not used).

The source is the Debian dfsg orig tarball because the upstream project is
published only through the Exelixis web site (no upstream git tag); the dfsg
tarball is byte-pinned by sha256.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout


class SweedConan(ConanFile):
    name = "sweed"
    version = "3.2.1"
    description = ("SweeD: maximum-likelihood detection of selective sweeps "
                   "from the site frequency spectrum")
    license = "GPL-2.0-or-later"
    homepage = "https://sco.h-its.org/exelixis/web/software/sweed/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sweed OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        opt = "-O3" if str(self.settings.build_type) == "Release" else "-O0 -g"
        # -fcommon: this 2012-era C uses tentative global definitions in headers;
        # modern clang defaults to -fno-common which would make them duplicate
        # symbols at link time.
        self.run('make -f Makefile.gcc CC="{}" CFLAGS="-Wall -fcommon {}" -j1'.format(cc, opt),
                 cwd=self.source_folder)
        if not os.path.isfile(os.path.join(self.source_folder, "SweeD")):
            raise ConanInvalidConfiguration("build did not produce the 'SweeD' program")

    def package(self):
        copy(self, "SweeD", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "README.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
