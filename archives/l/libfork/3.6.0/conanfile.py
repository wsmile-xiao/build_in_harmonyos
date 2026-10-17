#!/usr/bin/env python3
"""Conan recipe for libfork 3.6.0 — header-only C++23 fork-join library.

libfork is a header-only CMake library (INTERFACE target libfork::libfork,
requires C++23 coroutines and Threads). Optional hwloc/Boost-atomic features
are disabled (LF_NO_HWLOC=ON, LF_NO_BOOST_ATOMIC=ON) to keep zero required
dependencies; NUMA support falls back to the built-in topology detection.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibforkConan(ConanFile):
    name = "libfork"
    version = "3.6.0"
    package_type = "header-library"
    license = "MPL-2.0"
    homepage = "https://github.com/ConorWilliams/libfork"
    url = "https://github.com/ConorWilliams/libfork"
    description = "A bleeding-edge, lock-free, wait-free, continuation-stealing fork-join library built on C++20's coroutines."
    topics = ("multithreading", "fork-join", "parallelism", "coroutine", "lock-free", "wait-free")

    settings = "os", "compiler", "build_type", "arch"

    # Header-only: no compiled artifacts, package id is independent of settings.
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)
        # Mimic the packageConfig layout of the upstream CMake install rules.
        self.cpp.package.includedirs = [f"include/libfork-{self.version}"]
        self.cpp.package.bindirs = []
        self.cpp.package.libdirs = []

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Disable optional deps (hwloc / Boost.atomic) — zero required dependencies.
        tc.variables["LF_NO_HWLOC"] = "ON"
        tc.variables["LF_NO_BOOST_ATOMIC"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libfork")
        self.cpp_info.set_property("cmake_target_name", "libfork::libfork")
        # Coroutine/task schedulers require the threading runtime.
        self.cpp_info.system_libs = ["pthread"]
