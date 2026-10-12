#!/usr/bin/env python3
"""Conan recipe — zmat 1.0.0

ZMat is a portable C library (zmatlib.c/zmatlib.h) offering zlib/gzip/lzma/
lzip/lz4/lz4hc/zstd/blosc2/base64 data compression/decompression APIs
(zmat_run / zmat_encode / zmat_decode). All codec backends (miniz, easylzma,
lz4, zstd, blosc2) are bundled inside the upstream tarball; the `make lib`
target builds a self-contained static archive libzmat.a. No external Conan
dependencies.

Build system: pure Makefile (no configure script). `make lib` in src/ emits
    ../lib/libzmat.a (ROOTDIR defaults to the source tree root).

OHOS adaptation:
- zstd dict builder (blosc2/internal-complibs) references glibc-only
  qsort_r(); patches remove the forced _GNU_SOURCE so the portable C90
  qsort + g_coverCtx fallback is used (works on OHOS/musl, no platform
  macros introduced).
- Static build only (shared=False default): no .so signing needed, and the
  bundled codecs (including a zlib-compatible miniz) are linked into
  libzmat.a so there is no dynamic-linking conflict with system zlib (R26).

R32: settings.os gate uses in ("Linux", "OHOS").
R38: pure library, no CLI tool, no commands.json.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

import os


class ZmatConan(ConanFile):
    name = "zmat"
    version = "1.0.0"
    description = "ZMat: portable C library for inline data compression (zlib/gzip/lzma/lzip/lz4/lz4hc/zstd/blosc2/base64)"
    license = "GPL-3.0-only"
    homepage = "https://github.com/NeuroJSON/zmat"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # All codec backends are bundled in the upstream tarball (src/miniz,
        # src/easylzma, src/lz4, src/blosc2 incl. internal zstd). No external
        # Conan dependency (W0: preflight passed with no deps to publish).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "zmat supports only Linux and OHOS, got {}".format(self.settings.os))

    def _compiler_c(self):
        # R33: never rely on ambient ${CC} from the shell; take the compiler
        # from the Conan profile conf (set in ci/conan/profiles/ohos-aarch64).
        exes = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict)
        return exes.get("c", "clang")

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler_c()
        # `make -C src lib` produces ../lib/libzmat.a (ROOTDIR=.. -> src tree
        # root). POSIX_ENV=Yes makes uname-based platform detection see a
        # POSIX system. CC passed explicitly (E132-style safety, no shell CC).
        # -j1 keeps output deterministic for CI.
        make_cmd = ('make -C src lib -j1 "CC={cc}" "CXX={cc}++" POSIX_ENV=Yes'
                    .format(cc=cc))
        self.run(make_cmd, cwd=self.source_folder)

    def package(self):
        # No `make install` target upstream; copy artifacts directly.
        copy(self, "libzmat.a",
             src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "zmatlib.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["zmat"]
        self.cpp_info.set_property("cmake_file_name", "zmat")
        self.cpp_info.set_property("cmake_target_name", "zmat::zmat")
        # libzmat.a already contains all bundled codecs (miniz/lzma/lz4/zstd/
        # blosc2). OHOS libc provides pthread/dl symbols; no extra system_libs
        # are required (verified by linking example programs with only -lzmat).