#!/usr/bin/env python3
"""Conan recipe — catch 1.12.2

Catch is a modern, C++-native, header-only test framework for unit-tests,
TDD and BDD (the classic 1.x line of Catch2, upstream catchorg/Catch2 tag
v1.12.2). The package installs the single header single_include/catch.hpp;
its own self-test suite is exercised separately (see test_package/
MANIFEST.yml and reports/test-report.md). License: Boost Software License 1.0.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CatchConan(ConanFile):
    name = "catch"
    version = "1.12.2"
    description = "A modern, C++-native, header-only framework for unit-tests, TDD and BDD"
    license = "BSL-1.0"
    homepage = "https://github.com/catchorg/Catch2"
    url = "https://github.com/catchorg/Catch2"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only: nothing to compile; keep the patch-apply call for G1
        apply_conandata_patches(self)

    def package(self):
        copy(self, "catch.hpp",
             src=os.path.join(self.source_folder, "single_include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        # header-only: no build dependency on os/compiler/build_type
        self.info.clear()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Catch")
        self.cpp_info.set_property("cmake_target_name", "Catch::Catch")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
