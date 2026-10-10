#!/usr/bin/env python3
"""Conan recipe for the pinned upstream cpp-yyjson main snapshot."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class CppyyjsonConan(ConanFile):
    name = "cpp-yyjson"
    # User-requested snapshot identity: this tracks upstream main, not a release tag.
    version = "cpp-yyjson"
    description = "C++20 JSON wrapper backed by yyjson, pinned to upstream main"
    license = "MIT"
    homepage = "https://github.com/yosh-matsuda/cpp-yyjson"
    url = "https://github.com/yosh-matsuda/cpp-yyjson"
    topics = ("json", "yyjson", "cpp20")

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"build_tests": [True, False]}
    default_options = {"build_tests": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The pinned main snapshot bundles yyjson by default; only its upstream tests need GTest.
        if self.options.build_tests:
            self.requires("gtest/1.17.0.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload returns a tar.gz, but the commit-based URL has no filename extension.
        get(self, **self.conan_data["sources"], filename="cpp-yyjson-main.tar.gz", strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["CPPYYJSON_BUILD_TEST"] = "ON" if self.options.build_tests else "OFF"
        toolchain.variables["CPPYYJSON_BUILD_BENCH"] = "OFF"
        toolchain.variables["CPPYYJSON_USE_BUNDLED_YYJSON"] = "ON"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.build_tests:
            # Run the full upstream CTest suite explicitly for auditable CI logs.
            self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanrun")

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["cpp_yyjson"]
        self.cpp_info.set_property("cmake_file_name", "cpp_yyjson")
        self.cpp_info.set_property("cmake_target_name", "cpp_yyjson::cpp_yyjson")
