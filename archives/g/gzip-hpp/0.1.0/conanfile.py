#!/usr/bin/env python3
"""Conan recipe — gzip-hpp 0.1.0 (header-only C++ gzip compression library).

mapbox/gzip-hpp: light-weight header-only C++ library for gzip compression
and decompression, extracted from mapnik-vector-tile. Headers include
<zlib.h>, so consumers must link zlib (propagated via cpp_info.requires).

- package_type=header-library; headers are packaged as-is from include/gzip.
- Upstream tests (test/main.cpp + test/test_io.cpp + test/test_version.cpp)
  use Catch 1.x via mason; we build them against catch2/2.13.10 (registry)
  with a minimal include-path patch, linking registry zlib, and run them.
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class GzipHppConan(ConanFile):
    name = "gzip-hpp"
    version = "0.1.0"
    description = "gzip-hpp — header-only C++ library for gzip compression and decompression (mapbox)"
    license = "ISC"
    homepage = "https://github.com/mapbox/gzip-hpp"
    url = ""  # CI fills this
    topics = ("gzip", "zlib", "compression", "decompression", "header-only", "cpp11")

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    no_copy_source = True

    def layout(self):
        cmake_layout(self)

    def configure(self):
        # OHOS 适配 conan 对 settings.os.version 的枚举限制 (与 au 0.6.0 同问题)
        self.settings.rm_safe("os.version")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Header-only library: no compilation step; headers packaged as-is.
        pass

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gzip-hpp")
        self.cpp_info.set_property("cmake_target_name", "gzip-hpp::gzip-hpp")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # gzip-hpp headers include <zlib.h> and call zlib symbols; propagate
        # the zlib dependency to consumers at CMake level.
        self.cpp_info.requires = ["zlib::zlib"]
