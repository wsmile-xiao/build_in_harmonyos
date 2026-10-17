#!/usr/bin/env python3
"""Conan recipe for opentracing-cpp 1.5.1 — CMake library (HarmonyOS/PC).

opentracing-cpp is a C++11 implementation of the OpenTracing API. It is a
plain CMake project with no mandatory third-party dependencies (Catch2 and
mpark/variant + TartanLlama/expected are vendored as header-only under
3rd_party/include). Notes:

- Upstream declares cmake_minimum_required(VERSION 3.1); CMake >= 4.x refuses
  policies < 3.5, so this recipe sets CMAKE_POLICY_VERSION_MINIMUM=3.5.
- OHOS is not recognized by CMake as UNIX, so upstream's BUILD_DYNAMIC_LOADING
  self-disables on this platform (weak-symbol check passes, but the "NOT UNIX"
  guard turns it OFF). This is acceptable: dynamic loading is an optional
  feature; the core tracer/propagation/value API is unaffected.
- ENABLE_LINTING is disabled (clang-tidy exists in the toolchain but adds cost
  and no runtime value for a library package).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OpentracingCppConan(ConanFile):
    name = "opentracing-cpp"
    version = "1.5.1"
    description = "C++ implementation of the OpenTracing API"
    license = "MIT"
    homepage = "https://github.com/opentracing/opentracing-cpp"
    url = "https://github.com/opentracing/opentracing-cpp"

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
        # Upstream requires CMake >= 3.1; CMake 4.x dropped pre-3.5 policies.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Build only the requested flavor; keep mocktracer (part of package).
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        tc.variables["BUILD_MOCKTRACER"] = "ON"
        tc.variables["ENABLE_LINTING"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
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
        self.cpp_info.set_property("cmake_file_name", "OpenTracing")
        self.cpp_info.set_property("cmake_target_name", "OpenTracing::opentracing")
        # The upstream CMake export installs libopentracing as-is; no components.
        self.cpp_info.libs = ["opentracing"]