#!/usr/bin/env python3
"""Conan recipe — SeqAn 2.3.2 (header-only C++ library).

SeqAn is a header-only C++ library for biological sequence analysis.
This recipe packages the official library release asset
(seqan-library-2.3.2.tar.xz) which contains:
  - include/seqan/            (all headers)
  - lib/cmake/seqan/          (seqan-config.cmake + FindSeqAn.cmake support)
  - lib/pkgconfig/seqan-2.pc

No compilation is needed (R34 satisfied via test_package which includes
seqan headers and instantiates real API usage).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class SeqanConan(ConanFile):
    name = "seqan"
    version = "2.3.2"
    description = ("SeqAn - The Library for Sequence Analysis "
                   "(header-only, v2.3.2)")
    license = "BSD-3-Clause"
    homepage = "https://www.seqan.de"
    url = ""  # CI fills this

    package_type = "library"      # header-only

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # Header-only library: no compilation is required.
    # build() exists to satisfy the recipe skeleton; apply_conandata_patches
    # is a no-op because this release has no patches (patches: {}).
    def build(self):
        apply_conandata_patches(self)

    def package(self):
        pkg = self.package_folder
        # SeqAn headers live under include/seqan/
        copy(self, "*", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(pkg, "include"), keep_path=True)
        # CMake config + pkgconfig so consumers can find_package(SeqAn)
        copy(self, "*", src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(pkg, "lib"), keep_path=True)
        # License (shipped in share/doc/seqan in the release asset)
        copy(self, "LICENSE", src=os.path.join(self.source_folder, "share", "doc", "seqan"),
             dst=os.path.join(pkg, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # header-only: single package_id

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Allow find_package(SeqAn) via the shipped seqan-config.cmake
        self.cpp_info.builddirs = ["lib/cmake/seqan"]
        self.cpp_info.set_property("cmake_file_name", "seqan")
        self.cpp_info.set_property("cmake_target_name", "seqan::seqan")
        self.cpp_info.set_property("pkg_config_name", "seqan-2")