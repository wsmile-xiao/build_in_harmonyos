#!/usr/bin/env python3
"""Conan recipe — buildcache 0.28.6

A fast C/C++ compiler build cache (similar in spirit to ccache/sccache, but a
standalone C++ implementation). All third-party dependencies (lz4, xxHash,
zstd, hiredis, lua 5.3.4, cJSON, cpp-base64, HTTPRequest) are vendored inside
the source tree (src/third_party), so this recipe has no requirements() and is
fully self-contained.

Note: the project top-level CMakeLists.txt lives in the src/ subdirectory of
the source tarball, so CMake.configure() must use build_script_folder="src".

Build system: CMake (>= 3.16) + C++11
License: Zlib
Homepage: https://gitlab.com/bits-n-bites/buildcache
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class BuildcacheConan(ConanFile):
    name = "buildcache"
    version = "0.28.6"
    description = "A fast C/C++ compiler build cache"
    license = "Zlib"
    homepage = "https://gitlab.com/bits-n-bites/buildcache"
    url = "https://gitlab.com/bits-n-bites/buildcache"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # All third-party dependencies are vendored in the source tree
        # (src/third_party). No external Conan dependencies required.
        pass

    def layout(self):
        cmake_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OpenSSL is optional (only used for S3 HMAC + Redis TLS). Disable it to
        # avoid the OpenSSL assembly BAD_SIGNATURE issue on OHOS (E006); the
        # upstream Linux CI also builds with -DDISABLE_SSL=on.
        tc.variables["DISABLE_SSL"] = "ON"
        # C++11 is already enforced by upstream CMakeLists; keep it explicit to
        # guard against toolchain defaults (E096).
        tc.variables["CMAKE_CXX_STANDARD"] = 11
        tc.variables["CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_EXTENSIONS"] = "OFF"
        # R26: only static libraries are produced (the deliverable is a single
        # executable; no shared libraries).
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # The upstream project root CMakeLists.txt is in src/.
        cmake.configure(build_script_folder="src")
        # HMDFS: make jobserver relies on mkfifo (unsupported) — build single-threaded.
        cmake.build(cli_args=["-j1"])
        # Layer-1: run the upstream official test suite (8 ctest executables /
        # 40 TEST_CASE / 88 SUBCASE / 190 CHECK_EQ). The build and host profiles
        # are identical, so this is a native build and tests can run directly.
        if not cross_building(self):
            cmake.ctest()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
