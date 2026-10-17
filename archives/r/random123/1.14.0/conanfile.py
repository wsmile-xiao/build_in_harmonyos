#!/usr/bin/env python3
"""Conan recipe — random123 1.14.0 (header-only CBRNG library).

random123 (D. E. Shaw Research) is a collection of counter-based random
number generators implemented entirely in headers. The upstream package
has "nothing to build" (top-level GNUmakefile: 'Random123 is a
header-only package'); we install the include tree and expose it as a
header-library. No compile step, no linked libraries.
"""
from conan import ConanFile
import os
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class Random123Conan(ConanFile):
    name = "random123"
    version = "1.14.0"
    description = "Random123 - counter-based random number generators (header-only)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/DEShawResearch/random123"
    url = "https://github.com/DEShawResearch/random123"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # header-only, no runtime dependencies
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only package: nothing to compile. apply_conandata_patches
        # keeps patch support in sync with the CI input contract.
        apply_conandata_patches(self)

    def package(self):
        # header-only: install the include tree (Conan 2 copy uses fnmatch on
        # relative paths, so copy the whole dir with keep_path from source_folder)
        copy(self, "*",
             os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"), keep_path=True)

    def package_info(self):
        # header-only: no libraries to link
        self.cpp_info.set_property("cmake_file_name", "random123")
        self.cpp_info.set_property("cmake_target_name", "random123::random123")
