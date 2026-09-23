#!/usr/bin/env python3
"""Conan recipe - libspatialindex 1.9.3 (CMake, C++ spatial indexing library)."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LibspatialindexConan(ConanFile):
    name = "libspatialindex"
    version = "1.9.3"
    description = "Extensible framework for robust spatial indexing methods (R-tree, MVR-tree, TPR-tree)"
    license = "MIT"
    homepage = "https://github.com/libspatialindex/libspatialindex"
    url = ""
    topics = ("spatial-index", "rtree", "geometry")

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
        tc.variables["SIDX_BUILD_TESTS"] = False
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        if not self.options.shared:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.fPIC
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
        self.cpp_info.libs = ["spatialindex_c", "spatialindex"]
        # C++ 静态库消费者（含 C 驱动可执行）需要显式链接 libc++
        if not self.options.shared:
            self.cpp_info.system_libs = ["c++"]
