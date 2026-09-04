#!/usr/bin/env python3
"""Conan recipe — matchit 1.0.0 (CMake header-only / INTERFACE library).

matchit.cpp is a header-only C++17 pattern-matching library (single
include/matchit.h). Zero runtime dependencies; the whole public API lives in a
single header in include/.

Upstream build system: CMake INTERFACE target `matchit` with
target_include_directories(matchit INTERFACE include). Tests are gtest-driven
(test/matchit/*.cpp -> unittests + gtest_discover_tests) with samples added as
standalone executables (add_test(sample ...)).

Reference: archives/t/tsl-hopscotch-map/2.4.0/ (header-only CMake pattern).
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class MatchitConan(ConanFile):
    name = "matchit"
    version = "1.0.0"
    description = (
        "header-only C++17 pattern matching library (matchit.cpp, BowenFu) — "
        "match, some, as, ds, ooo, app, extractor, guards, ranges"
    )
    license = "MIT"
    homepage = "https://github.com/BowenFu/matchit.cpp"
    url = "https://github.com/BowenFu/matchit.cpp"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: accept OHOS as a Linux-family platform; upstream CMake has no
        # OHOS-specific logic (INTERFACE-only, no platform checks).
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            # Conan arch is "armv8"; CMake expects "aarch64"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Header-only INTERFACE library: nothing to compile. The upstream
        # gtest-driven test suite requires googletest fetched from GitHub over
        # the network (cmake/FetchGTest.cmake) which is not guaranteed in a
        # clean CI environment; upstream tests are therefore exercised locally
        # in the adaptation worktree (see test ledger) rather than inside
        # `conan create`. The consumer gate is the test_package in this recipe.
        pass

    def package(self):
        # pattern is relative to src; copy keeps the trailing directory of the
        # pattern, so join "include" in BOTH src and dst to avoid a doubled
        # include/include/matchit.h layout.
        copy(
            self,
            "matchit.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "matchit")
        self.cpp_info.set_property("cmake_target_name", "matchit::matchit")