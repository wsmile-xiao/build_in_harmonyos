#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches


class NetcdfCxxConan(ConanFile):
    name = "netcdf-cxx"
    version = "4.3.1"
    description = "Official netCDF C++ libraries and utilities"
    license = "Apache-2.0"
    homepage = "https://github.com/Unidata/netcdf-cxx4"
    package_type = "library"
    exports_sources = "patches/*"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def requirements(self):
        self.requires(
            "netcdf/4.9.3",
            transitive_headers=True,
            transitive_libs=True,
        )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["ENABLE_FORTRAN"] = "OFF"
        tc.variables["ENABLE_DAP"] = "OFF"
        tc.variables["ENABLE_TESTS"] = "OFF"
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
        self.cpp_info.libs = ["netcdf-cxx4"]
        self.cpp_info.requires = ["netcdf::netcdf"]
        self.cpp_info.set_property("cmake_file_name", "netcdf-cxx")
        self.cpp_info.set_property("cmake_target_name", "netcdf-cxx::netcdf-cxx")
        self.cpp_info.set_property("pkg_config_name", "netcdf-cxx4")
