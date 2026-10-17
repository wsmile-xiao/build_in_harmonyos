#!/usr/bin/env python3
"""Conan recipe — usrsctp 0.9.5.0 (SCTP userland library, CMake build).

E113: OHOS/musl system headers lack BSD-ish typedefs (u_int/u_long/u_short/
u_char/caddr_t) and gate `struct ifreq`/timeradd/timercmp behind
_GNU_SOURCE; usrsctp builds with -std=c99 -pedantic which suppresses them.
The 0001 patch adds ohos_compat.h (guard: not FreeBSD/APPLE/WIN32) and we
inject it with CMAKE_C_FLAGS=-include (E113 rec: add-cflags).
CMake >= 4 removed compatibility with cmake_minimum_required(VERSION 3.0),
so CMAKE_POLICY_VERSION_MINIMUM=3.5 is set to keep upstream CMakeLists valid.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class UsrsctpConan(ConanFile):
    name = "usrsctp"
    version = "0.9.5.0"
    description = "usrsctp - SCTP userspace implementation"
    license = "BSD-3-Clause"
    homepage = "https://github.com/sctplab/usrsctp"
    url = "https://github.com/sctplab/usrsctp"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder="source")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 removed support for cmake_minimum_required(VERSION 3.0)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Inject E113 compat header before any system header
        compat = self.source_folder + "/ohos_compat.h"
        tc.variables["CMAKE_C_FLAGS"] = "-include " + compat
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # library-only package: skip the optional example programs
        tc.variables["sctp_build_programs"] = "0"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["sctp_debug"] = "0"
        tc.variables["sctp_werror"] = "0"
        tc.variables["sctp_sanitizer_address"] = "0"
        tc.variables["sctp_sanitizer_memory"] = "0"
        tc.variables["sctp_build_fuzzer"] = "0"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["usrsctp"]