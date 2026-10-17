#!/usr/bin/env python3
"""Conan recipe for crossdb 0.14.0 — CMake, zero third-party dependencies.

crossdb is an embedded/server OLTP RDBMS written in C.  `src/crossdb.c` is an
amalgamation that #includes every subsystem, so one translation unit builds
`libcrossdb`; the upstream CMakeLists additionally builds the interactive
`xdb-cli` shell from the same amalgamation and installs both plus
`include/crossdb.h`.

Upstream ships a dual CMake + Makefile build system.  The CMake path is used
because it is the one that installs the library, the public header and the
CLI in a single step, and because it lets the upstream `test/` smoke suite be
wired in as a CTest target (patch 0001) instead of being compiled by hand.

OHOS / HarmonyOS portability patches (evidence in notes.md):
  0001  wire the upstream test/ smoke suite into CMake (opt-in, default OFF)
  0002  musl regex.h has no REG_STARTEND
  0003  musl libc exports no glibc-style qsort_r (ORDER BY)
  0004  plain char is unsigned on AArch64 (pkey_idx == -1 sentinel)
  0005  HMDFS rejects posix_fallocate() with EACCES
  0006  getopt() returns int, plus GNU --version/--help long options (L2 gate)
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class CrossdbConan(ConanFile):
    name = "crossdb"
    version = "0.14.0"
    description = "Ultra high-performance lightweight embedded and server OLTP RDBMS"
    license = "MPL-2.0"
    homepage = "https://crossdb.org"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # upstream crossdb has no third-party dependencies
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # build + register the upstream test/ smoke suite (patch 0001) so the
        # packaged build really runs it instead of assuming it passes
        tc.variables["XDB_BUILD_TESTS"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # upstream test/ smoke suite (test/xdb_smoke_test.c + utest.h):
        # 125 registered cases / 203 assertion sites.  --verbose so the case
        # list lands in the build log as evidence instead of a bare summary.
        self.run("ctest --verbose", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["crossdb"]
        # the package ships the upstream xdb-cli shell into bin/ (R38)
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        # upstream CMakeLists links pthread and dl for both targets
        self.cpp_info.system_libs = ["pthread", "dl"]
        self.cpp_info.set_property("cmake_file_name", "crossdb")
        self.cpp_info.set_property("cmake_target_name", "crossdb::crossdb")
