#!/usr/bin/env python3
"""Conan recipe for rapidfuzz-cpp 3.3.4 — header-only C++ fuzzy string matching.

rapidfuzz-cpp is a header-only library (CMake INTERFACE target `rapidfuzz`,
cxx_std_11). No compilation is needed for the library itself; this recipe
mirrors upstream `install(DIRECTORY rapidfuzz ...)` and copies the public
headers (`*.hpp` + `*.impl`) into the package include directory.

Upstream test suite (Catch2, under test/) was compiled and executed on the
HarmonyOS arm64 host during adaptation; evidence is in reports/.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class RapidfuzzcppConan(ConanFile):
    name = "rapidfuzz-cpp"
    version = "3.3.4"
    description = "Rapid fuzzy string matching in C++ (header-only, Levenshtein Distance and other algorithms)"
    license = "MIT"
    homepage = "https://github.com/rapidfuzz/rapidfuzz-cpp"
    url = "https://github.com/rapidfuzz/rapidfuzz-cpp"
    topics = ("fuzzy", "string-matching", "levenshtein", "header-only")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Header-only: no compilation needed. Upstream tests were verified on
        # the HarmonyOS arm64 host during adaptation (see reports/).

    def package(self):
        # Mirror upstream: install(DIRECTORY rapidfuzz -> include/ ... *.hpp *.impl)
        for pattern in ("*.hpp", "*.impl"):
            copy(
                self,
                pattern,
                src=os.path.join(self.source_folder, "rapidfuzz"),
                dst=os.path.join(self.package_folder, "include", "rapidfuzz"),
                keep_path=True,
            )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "rapidfuzz")
        self.cpp_info.set_property("cmake_target_name", "rapidfuzz::rapidfuzz")