#!/usr/bin/env python3
"""Conan recipe for boost 1.90.0 — header-only library.

Boost is header-only for most libraries (b2 build system incompatible with OHOS).
Only headers are installed, no compiled libraries. build() is a no-op since
package() copies the headers directly from source_folder to include/.
"""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostConan(ConanFile):
    name = "boost"
    version = "1.90.0"
    description = "Boost C++ Libraries 1.90.0 (header-only)"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "boost/*", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []