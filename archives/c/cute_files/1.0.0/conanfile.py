#!/usr/bin/env python3
"""Conan recipe — cute_files 1.0.0 (single-file header library).

cute_files is part of Randy Gaul's cute_headers collection. It is a
single-file C header implementing cross-platform directory traversal and
file-system utilities (cf_dir_open/cf_read_file/cf_dir_next/cf_dir_close,
cf_file_exists, cf_match_ext, cf_get_file_time, cf_traverse, ...).
Self-contained, no dynamic allocation, no external dependencies; supported
on Windows/macOS/POSIX (OHOS takes the UNIX branch).

Define CUTE_FILES_IMPLEMENTATION in exactly one translation unit that
includes the header to get the function definitions.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches
from conan.tools.layout import basic_layout


class CuteFilesConan(ConanFile):
    name = "cute_files"
    version = "1.0.0"
    description = "Single-file C header for directory traversal and file utilities"
    license = "Zlib OR Unlicense"
    homepage = "https://github.com/RandyGaul/cute_headers"
    url = "https://github.com/RandyGaul/cute_headers"
    topics = ("filesystem", "directory", "header-only", "c", "c-plus-plus", "traversal")

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # cute_files.h anchored at the official cute_headers_deprecated
        # commit 3d1931aa (header internal version v1.0, Copyright 2017
        # Randy Gaul) — the only official file of the 1.0.0 source.
        data = self.conan_data["sources"]["cute_files.h"]
        download(self, data["url"], os.path.join(self.source_folder, "cute_files.h"),
                 sha256=data["sha256"])
        apply_conandata_patches(self)

    def build(self):
        # Header-only: nothing to compile.
        pass

    def package(self):
        copy(self, "cute_files.h", self.source_folder,
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "cute_files")
        self.cpp_info.set_property("cmake_target_name", "cute_files::cute_files")
        self.cpp_info.set_property("pkg_config_name", "cute_files")