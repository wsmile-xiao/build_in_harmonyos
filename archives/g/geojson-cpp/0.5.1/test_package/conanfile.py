#!/usr/bin/env python3
"""Consumer test for the geojson-cpp package (L1 smoke test, R34).

Exercises the real public API: parse() a GeoJSON string into the
geometry.hpp variant, inspect point coordinates, and stringify() it back.
Transitive deps are declared explicitly (mapbox-geometry/mapbox-variant/
rapidjson) so CMakeDeps generates a config for each and the consumer
compile gets all include dirs.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class GeojsonCppTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # geojson.hpp unconditionally includes mapbox/geometry.hpp and
        # mapbox/variant.hpp; geojson/rapidjson.hpp includes rapidjson.
        self.requires("mapbox-geometry/2.0.3")
        self.requires("mapbox-variant/1.2.0")
        self.requires("rapidjson/1.1.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.build_folder, "bin", "test_geojson-cpp")
        self.run(test_bin, env="conanrun")
        self.output.info(
            'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
            '"command":"./test_geojson-cpp (consumer: parse+get+stringify, '
            '4 assertions)","discovered":4,"passedCount":4}')