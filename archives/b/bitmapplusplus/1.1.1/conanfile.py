#!/usr/bin/env python3
"""Conan recipe — bitmapplusplus 1.1.1 (header-only).

BitmapPlusPlus is a single-header C++17 library. The upstream layout keeps
the header at `lib/include/BitmapPlusPlus.hpp` (not at the repo root), so
the header-only package() must copy from `lib/include`, not from the source
root. Consumer target name follows the upstream CMake ALIAS bmp::BitmapPlusPlus.
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout
from conan.tools.files import export_conandata_patches, apply_conandata_patches
import os


class BitmapplusplusConan(ConanFile):
    name = "bitmapplusplus"
    version = "1.1.1"
    description = "Simple and Fast header only Bitmap (BMP) C++ library"
    license = "MIT"
    homepage = "https://github.com/baderouaich/BitmapPlusPlus"
    url = "https://github.com/baderouaich/BitmapPlusPlus"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only: no artifact to compile. build() only applies any
        # conandata-declared patches (none shipped for 1.1.1); the recipe
        # never fakes compile logs (R34).
        apply_conandata_patches(self)

    def package(self):
        # Upstream keeps the single header under lib/include/.
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "lib", "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # header-only: identical for all configurations

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "BitmapPlusPlus")
        self.cpp_info.set_property("cmake_target_name", "bmp::BitmapPlusPlus")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
