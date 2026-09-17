#!/usr/bin/env python3
"""Conan recipe for asyncfuture — header-only Qt library (variant A).

Upstream: https://github.com/vpicaver/asyncfuture (active fork of the
archived benlau/asyncfuture). Source tag: v1.1.0, packaged here as
version "1.0" per the platform task (platform version "1" + ".0" to
satisfy conan's >=2-char version validation).

Single public header (asyncfuture.h) + INTERFACE CMake target; no build
step. Consumers need Qt6::Core and Qt6::Concurrent.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class AsyncfutureConan(ConanFile):
    name = "asyncfuture"
    version = "1.0"
    description = "Use QFuture like a Promise object (header-only)"
    license = "Apache-2.0"
    homepage = "https://github.com/vpicaver/asyncfuture"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # asyncfuture.h consumes Qt types (QObject/QFuture); consumers need
        # Qt headers/libs transitively.
        self.requires("qtbase/6.11.1", transitive_headers=True,
                      transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # header-only: build() applies upstream patches only (none currently);
    # there is nothing to compile (R34 — no fake build log).
    def build(self):
        apply_conandata_patches(self)

    # Package config so CMake consumers can find_package(asyncfuture)
    # without CMakeDeps (qtbase sets cmake_find_mode=none, so CMakeDeps
    # can never emit a usable qtbase target for the link interface).
    _CONFIG_CMAKE = """\
# Minimal package config for the header-only asyncfuture library.
if(NOT TARGET asyncfuture::asyncfuture)
    get_filename_component(_ASYNCFUTURE_PREFIX
        "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
    add_library(asyncfuture::asyncfuture INTERFACE IMPORTED)
    set_target_properties(asyncfuture::asyncfuture PROPERTIES
        INTERFACE_INCLUDE_DIRECTORIES "${_ASYNCFUTURE_PREFIX}/include")
endif()
"""

    def package(self):
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        save(self, os.path.join(self.package_folder, "lib", "cmake",
                                "asyncfuture", "asyncfutureConfig.cmake"),
             self._CONFIG_CMAKE)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "asyncfuture")
        self.cpp_info.set_property("cmake_target_name", "asyncfuture::asyncfuture")
        # Qt headers/libs propagate via requirements() transitive_headers/
        # transitive_libs (qtbase 6.11.1 defines no "concurrent" component;
        # consumers find Qt6::Concurrent through Qt6Config.cmake directly).
