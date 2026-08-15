#!/usr/bin/env python3
"""Conan recipe for highway 1.3.0.1, Google's SIMD vector library."""

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import collect_libs, get


class HighwayConan(ConanFile):
    name = "highway"
    version = "1.3.0.1"
    description = "Performance-portable SIMD/vector intrinsics library"
    license = "Apache-2.0"
    homepage = "https://github.com/google/highway"
    url = "https://github.com/google/highway"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_upstream_tests": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)
        self.folders.build = "_build"
        self.folders.generators = "_build/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)

        upstream_tests = self.options.with_upstream_tests
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON" if upstream_tests else "OFF"
        tc.variables["HWY_ENABLE_CONTRIB"] = "ON" if upstream_tests else "OFF"
        tc.variables["HWY_ENABLE_EXAMPLES"] = "OFF"
        tc.variables["HWY_ENABLE_INSTALL"] = "ON"
        tc.variables["HWY_ENABLE_TESTS"] = "ON" if upstream_tests else "OFF"
        tc.variables["HWY_FORCE_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        # Highway's native runner preserves CTest discovery without downloading GTest.
        tc.variables["HWY_TEST_STANDALONE"] = "ON" if upstream_tests else "OFF"
        tc.variables["HWY_WARNINGS_ARE_ERRORS"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_upstream_tests and can_run(self):
            cmake.test(cli_args=["--output-on-failure", "--no-tests=error"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        libs = collect_libs(self)
        self.cpp_info.libs = libs or ["hwy"]
        self.cpp_info.set_property("cmake_file_name", "hwy")
        self.cpp_info.set_property("cmake_target_name", "hwy::hwy")
        self.cpp_info.set_property("pkg_config_name", "libhwy")
        if not self.options.shared:
            self.cpp_info.defines.append("HWY_STATIC_DEFINE")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
