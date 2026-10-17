#!/usr/bin/env python3
"""Conan recipe for serializer 0.5 — a single-header C++ serialization framework.

Upstream: https://github.com/eyalz800/serializer (MIT, header-only).
The library ships exactly one public header (serializer.h) and has no build
system of its own; this recipe installs the header and provides a C++17
consumer test that exercises the public save/load API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class SerializerConan(ConanFile):
    name = "serializer"
    version = "0.5"
    description = "A single header only standard C++ serialization framework"
    license = "MIT"
    homepage = "https://github.com/eyalz800/serializer"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.compiler.cppstd:
            from conan.tools.build import check_min_cppstd

            check_min_cppstd(self, "11")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        from conan.tools.cmake import CMakeToolchain

        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "17"
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        if self.settings.os in ("Linux", "OHOS"):
            # Keep CMake's platform logic usable with the OHOS Conan profile.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        # Header-only: nothing to compile for the package itself.
        pass

    def package(self):
        copy(self, "serializer.h", src=self.source_folder, dst=os.path.join(
            self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # header-only: single package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []