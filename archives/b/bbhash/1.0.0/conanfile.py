#!/usr/bin/env python3
"""Conan recipe — bbhash 1.0.0 (header-only minimal perfect hash library).

BBHash (github.com/rizkg/BBHash) is a single-header C++11 library:
the whole implementation lives in BooPHF.h and is included directly by
consumers, so nothing is compiled or linked here.  The upstream makefile
only builds the bundled test/sample programs (Bootest, example, ...),
which are not part of the distributed product, hence no commands.json
and no bin/ output (R38: library package, not a CLI tool).

Adaptation note: the header uses the BSD-ish typedef `u_int64_t` which is
not provided by the OHOS clang libc headers (no transitive <sys/types.h>
include).  The upstream patch adds `#include <sys/types.h>` so the header
compiles on OHOS aarch64 as well as on Linux/macOS.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BbhashConan(ConanFile):
    name = "bbhash"
    version = "1.0.0"
    description = "BBHash - minimal perfect hash function library (header-only)"
    license = "MIT"
    homepage = "https://github.com/rizkg/BBHash"
    url = "https://github.com/rizkg/BBHash"

    package_type = "header-library"

    # Header-only: no compiled artifacts, but keep settings for structure
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # No compilation step: header-only library (no fake build logs).
        apply_conandata_patches(self)

    def package(self):
        copy(self, "BooPHF.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # no build/compiler dependency -> single package_id

    def package_info(self):
        # Header-only: headers only, no libs, no bins.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
