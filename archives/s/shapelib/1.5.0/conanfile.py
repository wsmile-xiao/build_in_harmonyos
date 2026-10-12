#!/usr/bin/env python3
"""Conan recipe for shapelib 1.5.0 (CMake, zero external dependencies).

Shapelib is a C library for reading/writing ESRI Shapefiles.
Builds the static library libshp plus the upstream command-line utilities
(shpcreate, shpadd, shpdump, shprewind, dbfcreate, dbfadd, dbfdump, shptreedump).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ShapelibConan(ConanFile):
    name = "shapelib"
    version = "1.5.0"
    description = "C library for reading and writing ESRI Shapefiles"
    license = "LGPL-2.0-or-later"
    homepage = "https://shapelib.maptools.org/"
    url = ""  # CI fills this

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream ctest suite needs external EG_DATA (shape_eg_data.zip);
        # functional verification is done via test_package instead.
        tc.variables["BUILD_TEST"] = "OFF"
        # Upstream cmake_minimum_required(VERSION 2.8.5); CMake >= 4 removed
        # compatibility with < 3.5. Inject the policy escape hatch instead of
        # modifying upstream sources.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        self.cpp_info.set_property("cmake_file_name", "shapelib")
        self.cpp_info.set_property("cmake_target_name", "shp::shp")
        self.cpp_info.set_property("pkg_config_name", "shp")
        self.cpp_info.libs = ["shp"]
