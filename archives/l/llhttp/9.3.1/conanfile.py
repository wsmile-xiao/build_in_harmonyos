#!/usr/bin/env python3
"""Conan recipe — llhttp 9.3.1 (cmake).

llhttp is a port of http_parser to llparse, used for high-performance
HTTP request/response parsing. Originally part of Node.js.

Build system: CMake
License: MIT
No external dependencies.
No patches needed — source is fully compatible with OpenHarmony.
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LlhttpConan(ConanFile):
    name = "llhttp"
    version = "9.3.1"
    description = "HTTP parser — port of http_parser to llparse"
    license = "MIT"
    homepage = "https://github.com/nodejs/llhttp"
    url = ""  # CI fills this
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # llhttp has no external dependencies
        pass

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"llhttp supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # llhttp is NOT a system same-name library; build shared (default)
        tc.variables["LLHTTP_BUILD_SHARED_LIBS"] = "ON"
        tc.variables["LLHTTP_BUILD_STATIC_LIBS"] = "OFF"
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
        self.cpp_info.libs = ["llhttp"]
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = []
