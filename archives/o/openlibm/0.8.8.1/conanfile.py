#!/usr/bin/env python3
"""Conan recipe — openlibm 0.8.8 (Makefile project, no configure).

openlibm is a standalone BSD-licensed libm implementation built via
Makefile/Make.inc (targets: all -> libopenlibm.so + libopenlibm.a).
There is no ./configure script; the OHOS profile supplies clang via
tools.build:compiler_executables. Install rules are plain make install
(static + shared + pkgconfig + headers) honoring DESTDIR + prefix.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OpenlibmConan(ConanFile):
    name = "openlibm"
    version = "0.8.8.1"
    description = "Open source implementation of the C mathematical library (libm)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/JuliaMath/openlibm"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # openlibm has no external dependencies (standalone libm)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compiler from Conan conf (dict form), never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")

        # R9: -j1; make CC/AR/RANLIB explicit so the Makefile never falls back
        # to host gcc (empty on CI workers). openlibm builds in-tree, so run
        # make inside the *source* folder (the conan build folder is bare).
        # R26: default shared=False -> build only the static archive so
        # consumers never DT_NEEDED a .so whose absolute path (or missing
        # SONAME resolution) breaks on OHOS HMDFS at load time.
        targets = "libopenlibm.a" if not self.options.shared else "all"
        self.run(
            f"make CC={cc} CXX={cxx} AR={ar} RANLIB={ranlib} -j1 {targets}",
            cwd=self.source_folder,
        )

    def package(self):
        # openlibm install: libopenlibm.a + (optionally libopenlibm.so*) -> lib/,
        # headers -> include/openlibm, openlibm.pc -> lib/pkgconfig.
        # For shared=False (default) only install static + headers + pkgconfig.
        prefix = self.package_folder
        build = self.source_folder
        targets = "install-static install-headers install-pkgconfig" if not self.options.shared else "install"
        self.run(f"make DESTDIR= prefix={prefix} {targets} -j1", cwd=build)

        # harden: ensure key artifacts exist (fail fast in conan create)
        for rel in ("lib/libopenlibm.a", "include/openlibm/openlibm.h"):
            p = os.path.join(prefix, rel)
            if not os.path.exists(p):
                raise RuntimeError(f"missing expected package artifact: {p}")
        if self.options.shared and not os.path.exists(os.path.join(prefix, "lib/libopenlibm.so")):
            raise RuntimeError("missing expected shared artifact: lib/libopenlibm.so")

    def package_info(self):
        # openlibm installs headers under include/openlibm/ (matching its
        # own .pc file: Cflags: -I${includedir}/openlibm)
        self.cpp_info.includedirs = ["include/openlibm"]
        self.cpp_info.libs = ["openlibm"]