#!/usr/bin/env python3
"""Conan recipe for wrapsrv 1.0.0 -- a DNS SRV record command line wrapper.

Upstream builds a single translation unit (wrapsrv.c) with a plain Makefile:
    CC = gcc
    WARN = -Wall -Wextra -Werror
    CFLAGS = -O2 -g $(WARN)
    LDFLAGS = -lresolv

Two upstream assumptions do not hold on the HarmonyOS OHOS (musl based) libc:

* ``-lresolv`` -- OHOS ships the resolver inside ``libc``; there is no
  ``libresolv`` at all, so the linker flag is dropped and nothing is lost.
* ``ns_name_ntop()`` -- BIND's wire-format to presentation-format name
  renderer is declared by ``<arpa/nameser.h>`` but **not implemented** by the
  OHOS libc (``ld.lld-15: error: undefined symbol: ns_name_ntop``).  The
  missing conversion is re-implemented in-tree by patch 0001.

Everything else (all upstream sources, all upstream warning flags including
``-Werror``) is built unchanged, so the package is not trimmed in any way.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class WrapsrvConan(ConanFile):
    name = "wrapsrv"
    version = "1.0.0"
    description = "wrapsrv -- DNS SRV record command line wrapper (RFC 2782 weighted priority)"
    license = "Apache-2.0"
    homepage = "https://github.com/farsightsec/wrapsrv"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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

        # Upstream hardcodes CC=gcc in the Makefile. Take the cross compiler
        # from the Conan toolchain conf instead of relying on a shell
        # environment variable (R33).
        cc = self._c_compiler()

        # LDFLAGS is overridden to an empty value on purpose: upstream links
        # -lresolv, a glibc split library that OHOS does not ship (its
        # res_query()/ns_parserr() live in libc). CFLAGS keeps upstream's
        # -O2 -g -Wall -Wextra -Werror so the patch is compile-checked here.
        # (kept in sync with the upstream Makefile's own single link line)
        self.run(f"make CC=\"{cc}\" LDFLAGS=", cwd=self.source_folder)

    def package(self):
        copy(self, "wrapsrv", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # The pre-rendered roff man page is checked into the upstream tree;
        # upstream would regenerate it from wrapsrv.docbook with docbook2x-man.
        copy(self, "wrapsrv.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    def _c_compiler(self):
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        return executables.get("c") or "clang"
