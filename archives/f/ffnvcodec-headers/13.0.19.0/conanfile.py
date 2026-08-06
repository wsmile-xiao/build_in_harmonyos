#!/usr/bin/env python3
"""Conan recipe — ffnvcodec-headers (NVIDIA Video Codec SDK headers).

Header-only package providing NVENC/NVDEC API headers for FFmpeg.
Build: make all (generates ffnvcodec.pc) → copy headers + pkgconfig
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FfnvcodecHeadersConan(ConanFile):
    name = "ffnvcodec-headers"
    version = "13.0.19.0"
    description = "NVIDIA Video Codec SDK headers for NVENC/NVDEC"
    license = "MIT"
    homepage = "https://github.com/FFmpeg/nv-codec-headers"
    url = "https://github.com/FFmpeg/nv-codec-headers"

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
        # Generate ffnvcodec.pc from template (sed replaces @@PREFIX@@)
        self.run(f"make -C {self.source_folder} PREFIX={self.package_folder} all")

    def package(self):
        # Copy headers to include/ffnvcodec/
        copy(self, "*.h",
             os.path.join(self.source_folder, "include", "ffnvcodec"),
             os.path.join(self.package_folder, "include", "ffnvcodec"))
        # Copy generated pkg-config file from source folder
        copy(self, "ffnvcodec.pc",
             self.source_folder,
             os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("pkg_config_name", "ffnvcodec")
