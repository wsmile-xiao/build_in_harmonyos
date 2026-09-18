#!/usr/bin/env python3
"""Conan recipe — libmmmulti 0.1 (header-only, C++14).

Memory-mapped multimap, multiset, and interval tree.
The library is header-only (3 .hpp files in src/); no runtime library is produced.

Upstream dependencies:
  - sdsl-lite (static lib, NOT included — mmmultimap.hpp requires it)
  - ips4o (header-only, replaced with std::sort in source)
  - atomic_queue (header-only, conan requires)

This recipe bundles the source headers via exports_sources.
All upstream patches are applied directly in the source files.
Test coverage: mmmultiset + mmiitree (no sdsl dependency).
"""
from conan import ConanFile
from conan.tools.files import copy, apply_conandata_patches
from conan.tools.layout import basic_layout
import os


class LibmmmultiConan(ConanFile):
    name = "libmmmulti"
    version = "0.1"
    description = "Memory-mapped multimap, multiset, and interval tree"
    license = "MIT"
    homepage = "https://github.com/ekg/mmmulti"
    url = "https://salsa.debian.org/med-team/libmmmulti"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    # atomic_queue is a conan dependency; ips4o replaced with std::sort in source
    requires = "atomic_queue/1.9.2"

    # export_sources: bundle source files directly (no network download needed)
    exports_sources = "src/*.hpp", "LICENSE"

    def layout(self):
        basic_layout(self)

    def source(self):
        # Source is bundled via exports_sources; this method is intentionally minimal
        # Original source: https://salsa.debian.org/med-team/libmmmulti.git @ 275b129e
        pass

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # Copy libmmmulti headers
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        # Copy license
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libmmmulti")
        self.cpp_info.set_property("cmake_target_name", "libmmmulti::libmmmulti")
