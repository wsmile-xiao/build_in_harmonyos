#!/usr/bin/env python3
"""Conan recipe for unarr — decompression library for RAR/7z/ZIP/TAR archives.

Upstream build system: CMake. The optional upstream test suites are enabled so that
`cmake.test()` (build()) really runs them:
  - BUILD_INTEGRATION_TESTS: unarr-test over the archives from test/corpus
  - BUILD_UNIT_TESTS: crc32-test (needs cmocka, declared as a test requirement)
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class UnarrConan(ConanFile):
    name = "unarr"
    version = "1.1.1"
    description = ("A decompression library for RAR, 7z, ZIP and TAR archives "
                   "(used by unarr-based readers)")
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/selmf/unarr"
    url = "https://github.com/selmf/unarr"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # unarr prefers the system libraries (USE_SYSTEM_* default ON) for
        # zlib/bzip2/lzma when they are found by find_package().
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")
        self.requires("liblzma/5.8.1")

    def build_requirements(self):
        self.test_requires("cmocka/2.0.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Upstream CMakeLists looks for the canonical Find<T> imported targets
        # (ZLIB::ZLIB / BZip2::BZip2 / LibLZMA::LibLZMA); align the Conan-generated
        # target names with them so the libraries are actually linked in.
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.set_property("bzip2", "cmake_target_name", "BZip2::BZip2")
        deps.set_property("liblzma", "cmake_target_name", "LibLZMA::LibLZMA")
        deps.generate()
        tc = CMakeToolchain(self)
        # Upstream locates the compression libraries with CMake's Find modules
        # (find_package(BZip2/LibLZMA/ZLIB)); point those at the Conan packages so
        # every backend is really enabled instead of silently falling back.
        # ... and give the Find modules the exact paths, so the bzip2/xz backends are
        # enabled too (otherwise those upstream test entries are silently skipped).
        bzip2 = self.dependencies["bzip2"].package_folder
        liblzma = self.dependencies["liblzma"].package_folder
        zlib = self.dependencies["zlib"].package_folder
        tc.cache_variables["BZip2_ROOT"] = bzip2
        tc.cache_variables["BZIP2_INCLUDE_DIR"] = os.path.join(bzip2, "include")
        tc.cache_variables["BZIP2_LIBRARIES"] = os.path.join(bzip2, "lib", "libbz2.a")
        tc.cache_variables["LibLZMA_ROOT"] = liblzma
        tc.cache_variables["LIBLZMA_INCLUDE_DIR"] = os.path.join(liblzma, "include")
        tc.cache_variables["LIBLZMA_LIBRARY"] = os.path.join(liblzma, "lib", "liblzma.a")
        tc.cache_variables["LIBLZMA_LIBRARIES"] = os.path.join(liblzma, "lib", "liblzma.a")
        tc.cache_variables["ZLIB_ROOT"] = zlib
        tc.variables["BUILD_INTEGRATION_TESTS"] = True
        tc.variables["BUILD_UNIT_TESTS"] = True
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Upstream declares cmake_minimum_required(<3.5); CMake 4 removed that
        # compatibility, so keep the minimum policy version at 3.5.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream test suite must really run here (integration + unit tests).
        cmake.test()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["unarr"]
        self.cpp_info.set_property("cmake_file_name", "unarr")
        self.cpp_info.set_property("cmake_target_name", "unarr::unarr")
