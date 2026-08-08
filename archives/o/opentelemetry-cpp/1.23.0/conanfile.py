#!/usr/bin/env python3
"""Conan recipe for OpenTelemetry C++ 1.23.0 on HarmonyOS."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class OpenTelemetryCppConan(ConanFile):
    name = "opentelemetry-cpp"
    version = "1.23.0"
    description = "OpenTelemetry C++ API and SDK"
    license = "Apache-2.0"
    homepage = "https://opentelemetry.io"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "static-library"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables.update({
            "BUILD_SHARED_LIBS": False,
            "BUILD_TESTING": False,
            "WITH_BENCHMARK": False,
            "WITH_EXAMPLES": False,
            "WITH_FUNC_TESTS": False,
            "WITH_OTLP_GRPC": False,
            "WITH_OTLP_HTTP": False,
            "WITH_OTLP_FILE": False,
            "WITH_PROMETHEUS": False,
            "WITH_ZIPKIN": False,
            "WITH_ELASTICSEARCH": False,
            "WITH_OPENTRACING": False,
            "WITH_GSL": False,
            # WITH_STL is an upstream string enum (CXX11/CXX14/CXX17), not a
            # boolean CMake switch. CXX17 is required by this Conan profile.
            "WITH_STL": "CXX17",
            "OPENTELEMETRY_INSTALL": True,
            "OTELCPP_MAINTAINER_MODE": False,
        })
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = [
            "opentelemetry_trace",
            "opentelemetry_metrics",
            "opentelemetry_logs",
            "opentelemetry_resources",
            "opentelemetry_common",
            "opentelemetry_version",
        ]
        self.cpp_info.defines = ["OPENTELEMETRY_STL_VERSION=2017"]
        self.cpp_info.system_libs = ["pthread"]
        # The upstream package exports component-aware CMake targets such as
        # opentelemetry-cpp::api and propagates ABI-affecting compile
        # definitions from them.  Do not shadow those files with CMakeDeps.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [
            os.path.join("lib", "cmake", "opentelemetry-cpp")
        ]
