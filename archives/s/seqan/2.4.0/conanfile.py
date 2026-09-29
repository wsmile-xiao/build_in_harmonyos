#!/usr/bin/env python3
"""Conan recipe for SeqAn 2.4.0 (header-only, official library release).

SeqAn 2.x is a header-only C++ template library for sequence analysis. The
official `seqan-library-<version>` release asset already ships the final
layout (``include/seqan`` + ``share/cmake/seqan`` + ``share/pkgconfig``), so
the recipe only has to package it and expose the include directory.
"""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class SeqanConan(ConanFile):
    name = "seqan"
    version = "2.4.0"
    description = "SeqAn 2 - the C++ header-only library for sequence analysis"
    license = "BSD-3-Clause"
    homepage = "https://github.com/seqan/seqan"
    url = "https://github.com/seqan/seqan"
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def package_id(self):
        # Header-only: the package is identical for every setting.
        self.info.clear()

    def package(self):
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        # Upstream CMake find-module and pkg-config metadata (variables form:
        # SEQAN_INCLUDE_DIRS / SEQAN_LIBRARIES / SEQAN_DEFINITIONS).
        copy(
            self,
            "*.cmake",
            src=os.path.join(self.source_folder, "share", "cmake", "seqan"),
            dst=os.path.join(self.package_folder, "share", "cmake", "seqan"),
        )
        copy(
            self,
            "seqan-2.pc",
            src=os.path.join(self.source_folder, "share", "pkgconfig"),
            dst=os.path.join(self.package_folder, "share", "pkgconfig"),
        )
        copy(
            self,
            "LICENSE",
            src=os.path.join(self.source_folder, "share", "doc", "seqan"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "seqan")
        self.cpp_info.set_property("cmake_target_name", "seqan::seqan")
        self.cpp_info.set_property("pkg_config_name", "seqan-2")
