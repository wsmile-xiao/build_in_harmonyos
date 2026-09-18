#!/usr/bin/env python3
"""Conan recipe — exr_image 0.1.0-rc3 (standalone C89 single-header OpenEXR loader/writer).

exr_image.h is a header-only C89 library: consumers define EXR_IMAGE_IMPLEMENTATION
in exactly one translation unit and include the header. Nothing is compiled by the
recipe itself; the header plus the upstream test sources are packaged.

R32 note: no settings.os branch is needed — os=OHOS is handled by the OHOS-adapted
conan toolchain mapping (CMAKE_SYSTEM_NAME via CMakeToolchain/`os` setting).
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class ExrImageConan(ConanFile):
    name = "exr_image"
    version = "0.1.0-rc3"
    description = "exr_image - standalone C89 single-header library for loading and writing OpenEXR images"
    license = "MIT"
    homepage = "https://github.com/bartwe/exr_image"
    url = "https://github.com/bartwe/exr_image"  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # single-header library, no runtime dependencies
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only library: nothing to compile; apply any declared patches.
        apply_conandata_patches(self)

    def package(self):
        copy(self, "exr_image.h",
             src=os.path.join(self.source_folder, "."),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        # header-only: no libraries to link, public header installed
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []