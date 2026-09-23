#!/usr/bin/env python3
"""Conan recipe — thread-pool 4.1.0 (header-only C++17/C++20 thread pool library).

BS::thread_pool by Barak Shoshany, version 4.1.0. Header-only library with
two headers (include/BS_thread_pool.hpp, include/BS_thread_pool_utils.hpp);
the 4.1.0 tarball ships no build system (no CMake/autotools project).

Note: the same upstream is also archived as `bshoshany-thread-pool/5.x`.
This package follows the platform task name `thread-pool` for version 4.1.0.
v4.1.0 predates the native thread-affinity extensions introduced upstream in
5.x, and references no pthread_*_np symbols, so no OHOS musl patch is needed
(see notes.md).
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class ThreadPoolConan(ConanFile):
    name = "thread-pool"
    version = "4.1.0"
    description = "BS::thread_pool — a fast, lightweight, modern and easy-to-use C++17/C++20 thread pool library, header-only"
    license = "MIT"
    homepage = "https://github.com/bshoshany/thread-pool"
    url = "https://github.com/bshoshany/thread-pool"
    topics = ("thread-pool", "concurrency", "header-only", "cpp17", "cpp20")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Header-only library: no compilation step; headers are packaged as-is.
        # build() exists to satisfy G1 recipe-completeness gate (no-op for
        # header-only libraries without a CMake/meson/autotools project).
        pass

    def package(self):
        # v4.1.0 ships two headers under include/: the pool itself and the
        # independent utilities (BS::synced_stream, BS::signaller).
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "thread-pool")
        self.cpp_info.set_property("cmake_target_name", "thread-pool::thread-pool")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Header-only library: no libs to link.
        self.cpp_info.libs = []
