#!/usr/bin/env python3
"""Conan recipe — emhash 1.2.0 (header-only library, HarmonyOS).

emhash is a header-only C++17 open-addressing hash table library. There is
no compiled artifact: package() installs the public headers (emhash/, emilib/)
plus the aarch64 SSE2->NEON shim sse2neon.h (required by emilib headers on
OHOS aarch64 — the upstream CMake install excludes it, so the recipe copies it
explicitly, matching the upstream conanfile.py package()).
R34: consumer validation lives in test_package/ (test_consumer.cpp +
test_ohos.cpp), which include only installed public headers and run real API
calls with asserted observable results.
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
import os


class EmhashConan(ConanFile):
    name = "emhash"
    version = "1.2.0"
    description = "High-performance, memory-efficient C++ open addressing flat hash table (header-only)"
    license = "MIT"
    homepage = "https://github.com/ktprime/emhash"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # Header-only, but conan requires the shared option for package_type
    # "library"; package_id() clears it so a single package is produced.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, filename="emhash-1.2.0.tar.gz", **self.conan_data["sources"],
            strip_root=True)

    # Header-only: no compiled artifact, so build() applies the (empty)
    # patch set and does not run a fake compile (R34).
    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include", "emhash"),
             dst=os.path.join(self.package_folder, "include", "emhash"))
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include", "emilib"),
             dst=os.path.join(self.package_folder, "include", "emilib"))
        # aarch64 SSE2->NEON shim: emilib headers `#include <sse2neon.h>` on
        # OHOS aarch64; upstream CMake excludes it from install, so the recipe
        # copies it (same as upstream conanfile.py).
        copy(self, "sse2neon.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_id(self):
        self.info.clear()  # header-only: single package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
