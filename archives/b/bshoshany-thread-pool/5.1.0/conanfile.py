#!/usr/bin/env python3
"""Conan recipe — bshoshany-thread-pool 5.1.0 (single-file header-only C++ library).

BS::thread_pool by Barak Shoshany — a fast, lightweight, modern, and
easy-to-use C++17/C++20/C++23 thread pool library. True single-header
(include/BS_thread_pool.hpp), no CMake project, no dependencies.

5.1.0 changes vs 5.0.0: new native thread-affinity extension; on OHOS the
musl libc lacks the glibc pthread_*affinity_np() extensions, patched to use
sched_{get,set}affinity(0, ...) (pid 0 = calling thread) instead.
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BSThreadPoolConan(ConanFile):
    name = "bshoshany-thread-pool"
    version = "5.1.0"
    description = "BS::thread_pool — a fast, lightweight, modern and easy-to-use C++17/C++20/C++23 thread pool library, single-file header-only"
    license = "MIT"
    homepage = "https://github.com/bshoshany/thread-pool"
    url = "https://github.com/bshoshany/thread-pool"
    topics = ("thread-pool", "concurrency", "header-only", "cpp17", "cpp20", "cpp23")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Header-only library: no compilation step; headers are packaged as-is.
        # build() exists to satisfy G1 recipe-completeness gate (no-op for
        # single-header libraries without a CMake/meson/autotools project).
        pass

    def package(self):
        # True single-header library: copy include/BS_thread_pool.hpp.
        copy(self, "BS_thread_pool.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "bshoshany-thread-pool")
        self.cpp_info.set_property("cmake_target_name", "bshoshany-thread-pool::bshoshany-thread-pool")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Header-only library: no libs to link.
        self.cpp_info.libs = []
