#!/usr/bin/env python3
"""Conan recipe — libuecc 7 (CMake, BSD-2-Clause, no third-party deps).

Source: https://github.com/neocturne/libuecc (CHANGELOG v7: 2016/03/27)
License: BSD-2-Clause (per upstream COPYRIGHT)
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibueccConan(ConanFile):
    name = "libuecc"
    # Upstream identity: libuecc v7 (CHANGELOG v7, 2016/03/27).
    # Conan 2.x rejects single-segment versions ("7") and requires MAJOR.MINOR;
    # we declare the semver-normalized "7.0" while the archive directory keeps
    # the upstream label "7" for human readability. The artifacts registry
    # publishes under libuecc/7.0@ohpcd/stable.
    version = "7.0"
    description = "Very small Elliptic Curve Cryptography library compatible with Ed25519"
    license = "BSD-2-Clause"
    homepage = "https://github.com/neocturne/libuecc"
    url = "https://github.com/neocturne/libuecc"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libuecc v7 has no third-party runtime deps (per upstream CMakeLists.txt)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream CMakeLists.txt declares cmake_minimum_required(VERSION 2.6);
        # CMake 4.x refuses such old policy, so enforce CMP<3.5 deprecation cap.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        # Upstream produces uecc_shared / uecc_static with OUTPUT_NAME uecc.
        # CMakeDeps will create an imported target `libuecc::libuecc` (package
        # name reused) which links the actual archive named "uecc".
        self.cpp_info.libs = ["uecc"]
        # Upstream installs the public header to <prefix>/include/libuecc-7/libuecc/ecc.h,
        # so consumer code can keep the documented `#include <libuecc/ecc.h>` form
        # only when the include search path is `include/libuecc-7`. basic_layout's
        # default `include/` would search `<prefix>/include/libuecc/ecc.h` which
        # does not exist.
        self.cpp_info.includedirs = ["include/libuecc-7"]