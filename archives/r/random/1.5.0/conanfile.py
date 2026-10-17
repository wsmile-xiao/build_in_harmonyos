#!/usr/bin/env python3
"""Conan recipe — random 1.5.0 (header-only C++ random library).

effolkronium::random — "Random for modern C++" (single header
include/effolkronium/random.hpp). Zero runtime dependencies; the whole public
API lives in one header. Upstream build system: CMake INTERFACE target
`effolkronium_random` (no compiled objects); tests are Catch2-driven
(test/random_test.cpp -> random_static_test / random_thread_local_test /
random_local_test executables). Header-only -> no build() needed (R34: the
consumer gate is test_package, which actually includes and exercises the API).

Reference: archives/m/matchit/1.0.0/ (header-only CMake pattern).
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os


class RandomConan(ConanFile):
    name = "random"
    version = "1.5.0"
    description = "random 1.5.0 — Random for modern C++ (header-only)"
    license = "MIT"
    homepage = "https://github.com/ilqvya/random"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only: no compiled artifacts. apply_conandata_patches is a real
        # call that applies the (empty) patches:{} list — nothing to compile, so
        # no compile logs are produced or faked (R34); the consumer gate is the
        # test_package below, which includes and exercises the API.
        apply_conandata_patches(self)

    def package(self):
        # Keep the effolkronium/ directory so `#include "effolkronium/random.hpp"`
        # resolves with includedirs=["include"]. src is scoped to include/ so the
        # relative effolkronium/ subdir is preserved and test/catch.hpp is excluded.
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE.MIT",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()  # header-only: single package_id regardless of toolchain

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "random")
        self.cpp_info.set_property("cmake_target_name", "random::random")
