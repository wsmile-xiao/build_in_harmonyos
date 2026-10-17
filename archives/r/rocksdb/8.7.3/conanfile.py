#!/usr/bin/env python3
"""
Conan recipe for rocksdb 8.7.3 — CMake build system.

RocksDB is a high-performance embedded key-value store by Meta.

OHOS adaptation notes:
  - CMakeLists.txt patch: HarmonyOS platform detection (defines OS_LINUX so the
    `#if defined(OS_LINUX)` include guards in env/fs_posix.cc & env/io_posix.cc
    are satisfied, enabling sys/statfs.h / sys/sysmacros.h).
  - FAIL_ON_WARNINGS disabled: avoid -Werror with clang 15 on OHOS.
  - Source download uses conan get() with verify=False because the OHOS build
    environment lacks a valid CA bundle and curl; the SHA256 is still verified.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class RocksdbConan(ConanFile):
    name = "rocksdb"
    version = "8.7.3"
    description = "High-performance embedded key-value store for fast storage (Meta)"
    license = "Apache-2.0"
    homepage = "https://rocksdb.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("snappy/1.2.2")
        self.requires("lz4/1.10.0")
        self.requires("bzip2/1.0.8")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # verify=False: OHOS build env lacks valid CA bundle/curl; SHA256 still verified.
        get(self, **self.conan_data["sources"], strip_root=True, verify=False)
        apply_conandata_patches(self)

    def generate(self):
        # Ninja generator: `/bin/sh` is not usable by the default Unix Makefiles
        # generator in the OHOS container, so use Ninja which execs commands
        # directly.
        tc = CMakeToolchain(self, generator="Ninja")
        # Compression libraries
        tc.variables["WITH_ZLIB"] = "ON"
        tc.variables["WITH_SNAPPY"] = "ON"
        tc.variables["WITH_LZ4"] = "ON"
        tc.variables["WITH_BZ2"] = "ON"
        # zstd/gflags are shared-only on the ohpcd repo; the OHOS container
        # dynamic loader rejects loading user-writable-path shared libs, which
        # would block local test_package validation. Keep them OFF to yield a
        # statically-linkable, locally-validated build. zlib/snappy/lz4/bz2
        # (static) remain enabled, so RocksDB keeps compression support.
        tc.variables["WITH_ZSTD"] = "OFF"
        tc.variables["WITH_GFLAGS"] = "OFF"
        # Disable tests for main build
        tc.variables["WITH_TESTS"] = "OFF"
        tc.variables["WITH_TOOLS"] = "OFF"
        tc.variables["WITH_BENCHMARK_TOOLS"] = "OFF"
        tc.variables["WITH_CORE_TOOLS"] = "OFF"
        tc.variables["WITH_JNI"] = "OFF"
        tc.variables["WITH_JEMALLOC"] = "OFF"
        tc.variables["FAIL_ON_WARNINGS"] = "OFF"
        # Shared/static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Portable build for arm64
        tc.variables["PORTABLE"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["rocksdb"]
