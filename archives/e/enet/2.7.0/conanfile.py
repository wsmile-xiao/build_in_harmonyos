#!/usr/bin/env python3
"""Conan recipe for enet 2.7.0 — Reliable UDP networking library (pure C, CMake).

enet is a relatively thin, simple and robust network communication layer on top
of UDP. It provides connection management, reliable sequenced packet delivery,
channels and bandwidth throttling.

Upstream: https://github.com/zpl-c/enet  (MIT license)

OHOS adaptation notes (2.7.0):
  - 2.7.0 switched from autotools (1.3.18 era) to a native CMake build
    (CMakeLists.txt with ENET_STATIC / ENET_SHARED / ENET_TEST options).
    The library source is a single-TU implementation: the whole implementation
    lives in include/enet.h behind `ENET_IMPLEMENTATION`, and CMake compiles
    test/library.c (which only defines ENET_IMPLEMENTATION + includes enet.h)
    into libenet.a.  No configure step and no autoreconf needed.
  - ENET_TEST is kept OFF for the packaged library build; the upstream test
    executables (enet_test, enet_test_unit, enet_test_extra_peers,
    enet_test_ipv4_only) are built and run separately during adaptation
    validation, not installed into the package.
  - enet has no third-party runtime dependencies (pure C, only libc / sockets).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class EnetConan(ConanFile):
    name = "enet"
    version = "2.7.0"
    description = ("Reliable UDP networking library (thin layer over UDP with channels, "
                   "reliability, ordering, bandwidth throttling)")
    license = "MIT"
    homepage = "https://github.com/zpl-c/enet"
    url = "https://github.com/zpl-c/enet"  # CI rewrites as needed

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
        # R26: system-name libraries default to static; enet builds static by default upstream
        tc.variables["ENET_STATIC"] = "ON"
        tc.variables["ENET_SHARED"] = "ON" if self.options.shared else "OFF"
        # Tests are validated separately during adaptation, not packaged.
        tc.variables["ENET_TEST"] = "OFF"
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
        self.cpp_info.libs = ["enet"]