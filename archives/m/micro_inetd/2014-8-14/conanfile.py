#!/usr/bin/env python3
"""Conan recipe — micro_inetd 2014-8-14 (Makefile)"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class MicroInetdConan(ConanFile):
    name = "micro_inetd"
    version = "2014-8-14"
    description = "Simple network service spawner - inetd-style single-port/single-program connection spawner"
    license = "BSD-2-Clause"
    homepage = "https://www.acme.com/software/micro_inetd/"
    url = "https://www.acme.com/software/micro_inetd/"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler executables come from Conan conf, never from shell env.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")

        # Upstream CFLAGS use -ansi -pedantic -U__STRICT_ANSI__ (K&R-era
        # portability dance) plus a strict warning set; cross-compiling with
        # clang 15 for aarch64-linux-ohos passes with zero warnings, so the
        # flags are kept as-is. PIE is added for the L4 security scan.
        # Upstream LDFLAGS = -s (strip at link time) is intentionally NOT
        # passed: symbols are stripped by the release pipeline instead.
        cflags = (
            "-O -fPIE -pie -D_FORTIFY_SOURCE=2 -ansi -pedantic -U__STRICT_ANSI__ "
            "-Wall -Wpointer-arith -Wshadow -Wcast-qual -Wcast-align "
            "-Wstrict-prototypes -Wmissing-prototypes -Wmissing-declarations "
            "-Wredundant-decls -Wno-long-long"
        )
        # R9: -j1 (single translation unit anyway)
        self.run(
            f"make -C {self.source_folder} -j1 CC={cc} CFLAGS=\"{cflags}\" LDFLAGS=\"\""
        )

        # Upstream has no test suite (no check target, no test sources);
        # verification is done by test_package (see test_package/MANIFEST.yml).

    def package(self):
        # Upstream `install` target hardcodes /usr/local/{bin,man/man1} and
        # lacks mkdir -p, so install the artifacts directly instead of
        # driving `make install`.
        copy(
            self,
            "micro_inetd",
            self.source_folder,
            os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "micro_inetd.1",
            self.source_folder,
            os.path.join(self.package_folder, "share", "man", "man1"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
