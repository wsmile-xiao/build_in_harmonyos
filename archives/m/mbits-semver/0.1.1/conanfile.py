#!/usr/bin/env python3
"""Conan recipe for mbits-semver 0.1.1 — Semantic Version type for C++17.

Upstream: https://github.com/mbits-libs/semver (MIT, midnightBITS).
CMake static library; produces libsemver.a + semver headers + CMake export.
Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MbitssemverConan(ConanFile):
    name = "mbits-semver"
    version = "0.1.1"
    description = "Semantic Version type for C++17 (midnightBITS/mbits-libs)"
    license = "MIT"
    homepage = "https://github.com/mbits-libs/semver"
    url = "https://github.com/mbits-libs/semver"

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
        # Upstream standalone defaults enable self-tests + coveralls submodule;
        # the official tag tarball does not ship tools/coveralls (git submodule),
        # so self-tests stay OFF for the packaged library build (R26 static).
        tc.variables["SEMVER_TESTING"] = "OFF"
        tc.variables["SEMVER_INSTALL"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
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
        # Upstream target name is `semver` -> libsemver.a
        self.cpp_info.libs = ["semver"]
