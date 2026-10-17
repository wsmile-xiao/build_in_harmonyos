#!/usr/bin/env python3
"""test_package for libdart — real consumer validation.

Links only the installed (public) libdart headers and exercises the public C++
API with observable results: JSON parse (dart::packet::parse), typed field
access via the public view interface, programmatic construction
(dart::packet::make_object) and JSON serialization (to_json). Not a
print-only shell (R34 / L0c / PF3).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibdartTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The public libdart headers expose JSON parse/serialize only when
        # DART_HAS_RAPIDJSON is defined at compile time; a real consumer
        # provides RapidJSON headers to enable that headline feature.
        self.requires("rapidjson/1.1.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Directly run the consumer binary as well: executes the real
        # compiled consumer against the installed libdart headers.
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libdart")
        self.run(test_bin, env="conanrun")