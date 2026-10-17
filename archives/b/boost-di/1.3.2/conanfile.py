#!/usr/bin/env python3
"""Conan recipe — boost-di 1.3.2 (header-only C++14 dependency injection library).

Upstream: https://github.com/boost-ext/di
Header-only: the entire library ships as include/boost/di.hpp plus the
include/boost/di/ tree. No compiled artifacts; package just copies headers.
Note: upstream v1.3.2 tag keeps BOOST_DI_VERSION = 1'3'0 (patch release did
not bump the macro).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class BoostDiConan(ConanFile):
    name = "boost-di"
    version = "1.3.2"
    description = "C++14 Dependency Injection library (Boost.Ext.DI)"
    license = "BSL-1.0"
    homepage = "https://github.com/boost-ext/di"
    url = "https://github.com/boost-ext/di"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only library: no compiled artifacts, so nothing to build here.
        # Upstream tests are verified as a separate local gate (see
        # test_package/MANIFEST.yml ledger + notes.md) and by the L1
        # test_package consumer smoke test (R34).
        apply_conandata_patches(self)  # no-op when patches/ is empty

    def package(self):
        copy(self, "boost/di.hpp", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "boost/di/*", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        # Upstream ships no LICENSE file at repo root; the library is under the
        # Boost Software License 1.0 (see README badge). Skipped if absent.

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "boost-di")
        self.cpp_info.set_property("cmake_target_name", "boost-di::boost-di")
