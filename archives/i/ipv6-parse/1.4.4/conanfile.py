#!/usr/bin/env python3
"""Conan recipe — ipv6-parse 1.4.4 (CMake).

Upstream is a pure-C CMake library (project(ipv6 C) + add_library(ipv6-parse)).
R26: static build (system-name independent, but library is header-installable and
pkg-config based; static keeps the archive self-contained for OHOS).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Ipv6ParseConan(ConanFile):
    name = "ipv6-parse"
    version = "1.4.4"
    description = "Fast, RFC-compliant IPv6/IPv4 address parser with CIDR, port, and zone ID support"
    license = "MIT"
    homepage = "https://github.com/jrepp/ipv6-parse"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream CMakeLists supports an optional test executable set;
        # keep the library-only build (IPV6_PARSE_LIBRARY_ONLY=ON default).
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["IPV6_CONAN_BUILD"] = "ON"
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
        self.cpp_info.libs = ["ipv6-parse"]