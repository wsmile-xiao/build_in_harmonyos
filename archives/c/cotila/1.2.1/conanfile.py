#!/usr/bin/env python3
"""Conan recipe for cotila 1.2.1 — header-only compile-time linear algebra.

cotila ships only `include/cotila/**` headers (upstream CMake declares an
INTERFACE target and installs the header tree verbatim), so the recipe has
no build stage and no artifacts subject to E549 signing.  Upstream tests
pull doctest via CMake FetchContent (needs network at configure time) —
R51 declared: consumer-side verification is carried by test_package
(constexpr + runtime assertions) per R34.
"""
import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CotilaConan(ConanFile):
    name = "cotila"
    version = "1.2.1"
    description = "Compile-time linear algebra system for C++"
    license = "Apache-2.0"
    homepage = "https://github.com/calebzulawski/cotila"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only: nothing to compile (and no fake build logs — R34).
        # Apply declared patches to the source tree if any are ever added.
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_target_name", "cotila::cotila")
        self.cpp_info.set_property("cmake_file_name", "cotila")
