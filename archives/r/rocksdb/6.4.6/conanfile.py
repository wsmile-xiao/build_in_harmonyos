#!/usr/bin/env python3
"""
Conan recipe for rocksdb 6.4.6 — CMake build system.

RocksDB is a high-performance embedded key-value store by Meta.

OHOS adaptation notes:
  - CMakeLists.txt patch: HarmonyOS platform detection (OS_LINUX)
  - CMakeLists.txt patch: C++11 → C++17 upgrade (OHOS SDK libc++ requires C++17)
  - CMakeLists.txt patch: musl header force-include to avoid sysroot conflicts
  - CMakeLists.txt patch: shared lib CXX_STANDARD 11 → 17
  - env/env_posix.cc: __OHOS__ guard for POSIX header includes
  - env/io_posix.cc: __OHOS__ guard for POSIX header includes
  - util/channel.h: mutable std::mutex for C++17 const method compatibility
  - CMAKE_POLICY_VERSION_MINIMUM=3.5: rocksdb 6.4.6 requires cmake < 3.5
  - FAIL_ON_WARNINGS disabled: avoid -Werror with clang 15 on OHOS
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches
import os


class RocksdbConan(ConanFile):
    name = "rocksdb"
    version = "6.4.6"
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
        self.requires("zstd/1.5.6")
        self.requires("bzip2/1.0.8")
        self.requires("gflags/2.2.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Use curl + tar --strip-components: Gitee mirror + Python SSL issue on OHOS
        src = self.conan_data["sources"]
        url = src["url"]
        sha256 = src["sha256"]
        tarball = "rocksdb-6.4.6.tar.gz"
        self.run(f"curl -sL -o {tarball} '{url}'")
        # Verify sha256
        import hashlib
        with open(tarball, "rb") as f:
            computed = hashlib.sha256(f.read()).hexdigest()
        if computed != sha256:
            raise Exception(f"SHA256 mismatch: expected {sha256}, got {computed}")
        # Extract with strip-components=1 to remove top-level directory
        self.run(f"tar xzf {tarball} --strip-components=1")
        os.remove(tarball)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Compression libraries
        tc.variables["WITH_ZLIB"] = "ON"
        tc.variables["WITH_SNAPPY"] = "ON"
        tc.variables["WITH_LZ4"] = "ON"
        tc.variables["WITH_ZSTD"] = "ON"
        tc.variables["WITH_BZ2"] = "ON"
        tc.variables["WITH_GFLAGS"] = "ON"
        # Disable tests for main build
        tc.variables["WITH_TESTS"] = "OFF"
        tc.variables["WITH_TOOLS"] = "OFF"
        tc.variables["WITH_BENCHMARK_TOOLS"] = "OFF"
        tc.variables["WITH_CORE_TOOLS"] = "OFF"
        tc.variables["WITH_JNI"] = "OFF"
        tc.variables["WITH_JEMALLOC"] = "OFF"
        # Disable -Werror
        tc.variables["FAIL_ON_WARNINGS"] = "OFF"
        # Shared/static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Portable build for arm64
        tc.variables["PORTABLE"] = "ON"
        # cmake policy: rocksdb 6.4.6 requires cmake < 3.5
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
