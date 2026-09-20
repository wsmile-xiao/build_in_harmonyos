#!/usr/bin/env python3
"""Conan recipe for memsafe 0.4.0 — header-only C++20 memory-safety library.

The upstream project is a header-only library (memsafe.h) plus an optional
clang compiler plugin (memsafe_clang.cpp -> memsafe_clang.so).  The plugin is
a development-time static-analysis tool tied to a specific clang version
(upstream targets clang-20 APIs); it is NOT part of the library deliverable
and is not packaged here.  This recipe ships the public header only.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class MemsafeConan(ConanFile):
    name = "memsafe"
    version = "0.4.0"
    description = "Memory safety for C++ (header-only library, safe shared_ptr/weak_ptr wrappers)"
    license = "MIT"
    homepage = "https://github.com/rsashka/memsafe"
    url = "https://github.com/rsashka/memsafe"

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

    def package(self):
        # Header-only library: ship memsafe.h.  memsafe_plugin.h is only for the
        # clang plugin (requires yaml-cpp) and is not part of the library API.
        copy(self, "memsafe.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
