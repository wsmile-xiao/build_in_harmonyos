#!/usr/bin/env python3
"""Conan recipe for TinyXML 2.6.2.

TinyXML 2.x ships a small GNU Makefile but no install target or CMake build.
The package supplies a minimal CMake entry point so Conan can cross-compile the
library with its OHOS toolchain while keeping the upstream implementation
unchanged.
"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class TinyxmlConan(ConanFile):
    name = "tinyxml"
    version = "2.6.2"
    description = "Small, simple C++ XML parser"
    license = "Zlib"
    homepage = "https://sourceforge.net/projects/tinyxml/"
    url = "https://sourceforge.net/projects/tinyxml/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False], "with_stl": [True, False]}
    default_options = {"shared": False, "fPIC": True, "with_stl": True}

    exports_sources = "CMakeLists.txt"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["TINYXML_USE_STL"] = bool(self.options.with_stl)
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
        self.cpp_info.libs = ["tinyxml"]
        self.cpp_info.set_property("cmake_file_name", "tinyxml")
        self.cpp_info.set_property("cmake_target_name", "tinyxml::tinyxml")
        self.cpp_info.set_property("pkg_config_name", "tinyxml")
        if self.options.with_stl:
            self.cpp_info.defines.append("TIXML_USE_STL")
