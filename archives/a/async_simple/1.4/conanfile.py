#!/usr/bin/env python3
"""Conan recipe — async_simple 1.4 (CMake)

alibaba C++20 async framework: coroutine, uthread, Future/Promise.
Source: https://github.com/alibaba/async_simple
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AsyncSimpleConan(ConanFile):
    name = "async_simple"
    version = "1.4"
    description = "alibaba C++20 async framework with coroutine and uthread support"
    license = "Apache-2.0"
    homepage = "https://github.com/alibaba/async_simple"
    url = "https://github.com/alibaba/async_simple"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Force C++20 (async_simple requires coroutines, CI profile may use cppstd=17)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # E092: CMake does not recognize HarmonyOS, set Linux to enable uthread
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Disable AIO (libaio not available on OHOS)
        tc.variables["ASYNC_SIMPLE_DISABLE_AIO"] = "ON"
        # Disable tests in conan build (googletest is a system prebuilt, not conan dep)
        tc.variables["ASYNC_SIMPLE_ENABLE_TESTS"] = "OFF"
        tc.variables["ASYNC_SIMPLE_ENABLE_ASAN"] = "OFF"
        tc.variables["ASYNC_SIMPLE_BUILD_DEMO_EXAMPLE"] = "OFF"
        tc.variables["ASYNC_SIMPLE_BUILD_MODULES"] = "OFF"
        # Override -Werror in upstream CMakeLists.txt
        tc.extra_cxxflags.append("-Wno-error")
        tc.extra_cxxflags.append("-Wno-deprecated-register")
        tc.extra_cxxflags.append("-Wno-mismatched-new-delete")
        tc.extra_cxxflags.append("-Wno-deprecated-declarations")
        tc.extra_cxxflags.append("-Wno-uninitialized")
        tc.extra_cxxflags.append("-Wno-unused-value")
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
        self.cpp_info.libs = ["async_simple"]
        self.cpp_info.system_libs = ["pthread"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.cxxflags.append("-std=c++20")
