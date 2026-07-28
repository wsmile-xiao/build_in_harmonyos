#!/usr/bin/env python3
"""Conan recipe for IXWebSocket 12.0.1 — CMake-based WebSocket library.

Build system: CMake
Dependencies: zlib/1.3.1, openssl/3.5.6 (optional, for TLS)
License: BSD-3-Clause
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps
from conan.tools.layout import basic_layout


class IxwebsocketConan(ConanFile):
    name = "ixwebsocket"
    version = "12.0.1"
    description = "Lightweight WebSocket client and server library for C++"
    license = "BSD-3-Clause"
    homepage = "https://github.com/machinezone/IXWebSocket"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "use_tls": [True, False],
        "use_zlib": [True, False],
    }
    default_options = {
        "shared": False,
        "use_tls": True,
        "use_zlib": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.use_zlib:
            self.requires("zlib/1.3.1")
        if self.options.use_tls:
            self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Static by default to avoid polluting system lib paths
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["USE_TLS"] = self.options.use_tls
        tc.variables["USE_ZLIB"] = self.options.use_zlib
        tc.variables["USE_WS"] = False
        tc.variables["USE_TEST"] = False
        tc.variables["BUILD_DEMO"] = False
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ixwebsocket")
        self.cpp_info.set_property("cmake_target_name", "ixwebsocket::ixwebsocket")
        self.cpp_info.set_property("pkg_config_name", "ixwebsocket")
        self.cpp_info.libs = ["ixwebsocket"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        if self.options.use_tls:
            self.cpp_info.defines.append("IXWEBSOCKET_USE_TLS")
        if self.options.use_zlib:
            self.cpp_info.defines.append("IXWEBSOCKET_USE_ZLIB")
