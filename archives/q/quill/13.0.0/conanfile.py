#!/usr/bin/env python3
"""Conan recipe — quill 13.0.0 (CMake header-only C++17 logging library).

quill is an INTERFACE (header-only) CMake target plus bundled fmt headers.
It requires Threads at consumption time. There is no compiled library
output (src/quill.cc is only used for the experimental C++20 module build).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class QuillConan(ConanFile):
    name = "quill"
    version = "13.0.0"
    description = "Asynchronous Low Latency C++ Logging Library"
    license = "MIT"
    homepage = "https://github.com/odygrd/quill"
    url = "https://github.com/odygrd/quill"
    topics = ("logging", "async", "low-latency", "header-only")
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    exports_sources = "CMakeLists.txt", "cmake/*", "include/*", "src/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Install target is only enabled when quill is a subproject,
        # so force it ON so `cmake --install` exports the headers.
        tc.variables["QUILL_ENABLE_INSTALL"] = "ON"
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
        self.cpp_info.set_property("cmake_file_name", "quill")
        self.cpp_info.set_property("cmake_target_name", "quill::quill")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.requires = []
        if not self.settings.os in ("Windows", "Android"):
            self.cpp_info.system_libs.append("pthread")
