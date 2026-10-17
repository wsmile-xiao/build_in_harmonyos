#!/usr/bin/env python3
"""Conan test_package — websocketpp 0.8.2.1 consumer test.

Verifies the package the way autobahn-cpp will consume it:
find_package(Websocketpp) from the Conan-generated config, then exercises
real library APIs (URI parsing, base64 round-trip, UTF-8 validation, close
status constants) and instantiates the Boost.Asio client template that
autobahn-cpp links against.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class WebsocketppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_websocketpp"),
                 env="conanrun")
