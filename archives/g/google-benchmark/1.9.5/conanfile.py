#!/usr/bin/env python3
"""Conan recipe for Google Benchmark 1.9.5.

Build system: CMake (library: libbenchmark.a + libbenchmark_main.a, header include/benchmark/).
No external dependencies (bundled gtest disabled for library build).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class GoogleBenchmarkConan(ConanFile):
    name = "google-benchmark"
    version = "1.9.5"
    description = "A library to benchmark code snippets, similar to unit tests"
    license = "Apache-2.0"
    homepage = "https://github.com/google/benchmark"
    url = "https://github.com/google/benchmark"
    topics = ("benchmark", "testing", "performance", "c++")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BENCHMARK_ENABLE_TESTING"] = "OFF"
        tc.variables["BENCHMARK_ENABLE_GTEST_TESTS"] = "OFF"
        tc.variables["BENCHMARK_ENABLE_INSTALL"] = "ON"
        tc.variables["BENCHMARK_INSTALL_DOCS"] = "OFF"
        tc.variables["BENCHMARK_ENABLE_DOXYGEN"] = "OFF"
        tc.variables["BENCHMARK_ENABLE_LTO"] = "OFF"
        tc.variables["BENCHMARK_ENABLE_WERROR"] = "OFF"
        tc.variables["BENCHMARK_ENABLE_EXCEPTIONS"] = "ON"
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
        self.cpp_info.libs = ["benchmark"]
        self.cpp_info.set_property("cmake_file_name", "benchmark")
        self.cpp_info.set_property("cmake_target_name", "benchmark::benchmark")
        self.cpp_info.set_property("pkg_config_name", "benchmark")