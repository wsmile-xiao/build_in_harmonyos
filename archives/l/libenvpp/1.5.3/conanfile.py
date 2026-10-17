#!/usr/bin/env python3
"""Conan recipe — libenvpp 1.5.3 (CMake project, C++17 header+static library).

libenvpp is an environment-variable parsing library. Upstream CMakeLists uses
FetchContent from external/fmt (empty submodule placeholder in the release
tarball), so fmt is required from the OHPC registry and LIBENVPP_USE_SYSTEM_DEPS
is enabled to consume it via find_package. Catch2 is only needed for upstream
tests (LIBENVPP_TESTS=OFF for packaging; upstream tests are run separately).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class LibenvppConan(ConanFile):
    name = "libenvpp"
    version = "1.5.3"
    description = "libenvpp is a C++ library for parsing and validating environment variables."
    license = "MIT"
    homepage = "https://github.com/ph3at/libenvpp"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libenvpp 公开头包含 <fmt/format.h>，消费者需传递获得 fmt 头文件。
        # 使用本仓库已发布的 fmt/12.2.0（含 <fmt/std.h>、fmt::ostream_formatter）。
        self.requires("fmt/12.2.0", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # fmt is provided by the Conan dependency instead of the (empty)
        # upstream submodule placeholder; Catch2 is not packaged.
        tc.variables["LIBENVPP_USE_SYSTEM_DEPS"] = "ON"
        tc.variables["LIBENVPP_TESTS"] = "OFF"
        tc.variables["LIBENVPP_EXAMPLES"] = "OFF"
        tc.variables["LIBENVPP_INSTALL"] = "ON"
        tc.generate()
        cmake_deps = CMakeDeps(self)
        cmake_deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["envpp"]
        self.cpp_info.requires = ["fmt::fmt"]
