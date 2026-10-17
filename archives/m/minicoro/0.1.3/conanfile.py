#!/usr/bin/env python3
"""Conan recipe — minicoro 0.1.3 (single-file asymmetric coroutine C library).

minicoro is a single-header C library for asymmetric stackful coroutines,
inspired by Lua coroutines. The implementation is selected at compile time
by the consumer via `#define MINICORO_IMPL` in exactly one translation unit.
No library binary is produced by upstream — consumers compile the header
into their own TU. For aarch64 (aarch64-linux-ohos) the header uses its
dedicated MCO_USE_ASM implementation (minicoro.h line ~1081 `__aarch64__`),
so no OHOS-specific source patch is required.

Build system: none (header-only). Upstream tests live in tests/ and are
driven by a plain Makefile; upstream test enumeration is recorded in
test_package/MANIFEST.yml.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MinicoroConan(ConanFile):
    name = "minicoro"
    version = "0.1.3"
    description = "Single-file header-only asymmetric stackful coroutine library for C"
    license = "MIT"
    homepage = "https://github.com/edubart/minicoro"
    url = "https://github.com/edubart/minicoro"

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def requirements(self):
        # Header-only C89 library: only libc / pthread (upstream mt-example)
        # are needed at runtime; no third-party Conan dependency.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # No library binary to build; consumers define MINICORO_IMPL in one
        # TU. Keep the patch hook for recipe consistency (R30 gate).
        apply_conandata_patches(self)

    def package(self):
        copy(self, "minicoro.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "minicoro")
        self.cpp_info.set_property("cmake_target_name", "minicoro")
        self.cpp_info.names["cmake_find_package"] = "minicoro"
        self.cpp_info.names["cmake_find_package_multi"] = "minicoro"