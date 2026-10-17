#!/usr/bin/env python3
"""Conan recipe for websocketpp 0.8.2 — C++ WebSocket client/server library.

Header-only library built on Boost.Asio. The upstream CMake install only
copies headers (websocketpp/CMakeLists.txt -> final_target() installs the
whole include tree with PATTERN "*.hpp*") and no compiled object, so this
recipe installs the headers directly instead of driving the ancient
cmake_minimum_required(2.8.8) project under CMake 4.x.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class WebsocketppConan(ConanFile):
    name = "websocketpp"
    version = "0.8.2"
    description = (
        "WebSocket client/server library for C++ built on Boost.Asio "
        "(header-only)"
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/zaphoyd/websocketpp"
    url = "https://github.com/zaphoyd/websocketpp"
    topics = ("websocket", "asio", "boost", "header-only")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    # R32: no shared option for a header-only package

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # common/memory.hpp, common/functional.hpp etc. fall back to Boost
        # smart pointers; transport/asio/*.hpp includes <boost/asio.hpp>
        # unconditionally for the asio transport (the config autobahn-cpp
        # and most consumers use).
        self.requires("boost/1.90.0")
        # The TLS-capable configs (config/asio.hpp, config/asio_client.hpp)
        # include <boost/asio/ssl.hpp>, which pulls in <openssl/*.h>. The
        # boost/1.90.0 package in this repo does not carry an OpenSSL
        # dependency, so a websocketpp consumer would otherwise fail with
        # "openssl/conf.h file not found" while compiling those headers.
        self.requires("openssl/3.5.6")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "websocketpp"),
             dst=os.path.join(self.package_folder, "include", "websocketpp"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Consumers in this repo (autobahn-cpp cmake/Modules/FindWebsocketpp.cmake,
        # upstream websocketpp-config.cmake.in) name the package "Websocketpp".
        self.cpp_info.set_property("cmake_file_name", "Websocketpp")
        self.cpp_info.set_property("cmake_target_name", "websocketpp::websocketpp")
        self.cpp_info.set_property("pkg_config_name", "websocketpp")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
