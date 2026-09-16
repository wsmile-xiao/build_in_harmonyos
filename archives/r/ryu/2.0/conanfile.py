#!/usr/bin/env python3
"""Conan 2.x recipe — Ryu 2.0 (C implementation of the Ryu float-to-string algorithm)

Upstream (https://github.com/ulfjack/ryu, tag v2.0) uses Bazel (BUILD files)
and ships no configure/CMake entry point. This recipe follows the repo-wide
pattern for build-system-less upstreams (cf. archives/a/alac/0.0.7): it ships
a minimal CMakeLists.txt via export_sources() that compiles the upstream
default cc_library target `//ryu` (ryu/d2s.c + ryu/f2s.c, public header
ryu/ryu.h). Upstream optional components (generic_128, ryu_printf) are
separate Bazel cc_libraries and are intentionally not part of this package;
see notes.md for the rationale and the aarch64 long-double caveat of
generic_128.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class RyuConan(ConanFile):
    name = "ryu"
    version = "2.0"
    description = "Ryu algorithm: shortest float/double to decimal string conversion (C implementation)"
    license = "Apache-2.0 OR BSL-1.0"
    homepage = "https://github.com/ulfjack/ryu"
    url = "https://github.com/ulfjack/ryu"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def validate(self):
        # R32: OHOS platform must be accepted alongside Linux
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26-style default: static library unless explicitly requested
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
        # Dual license upstream: Apache-2.0 OR Boost (BSL-1.0)
        copy(self, "LICENSE-Apache2", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE-Boost", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["ryu"]
