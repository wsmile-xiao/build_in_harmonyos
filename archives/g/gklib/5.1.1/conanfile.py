#!/usr/bin/env python3
"""Conan recipe for GKlib 5.1.1."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class GKlibConan(ConanFile):
    name = "gklib"
    version = "5.1.1"
    description = "Helper routines and data structures used by KarypisLab software"
    license = "Apache-2.0"
    homepage = "https://github.com/KarypisLab/GKlib"
    topics = ("graph", "algorithms", "data-structures")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        os_name = str(self.settings.os)
        if os_name not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("GKlib is packaged for Linux/OHOS")
        if os_name == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("GKlib supports OHOS armv8 only")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        if os.name == "nt":
            toolchain.generator = "Ninja"
        if str(self.settings.os) == "OHOS":
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        toolchain.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.cache_variables["OPENMP"] = False
        toolchain.cache_variables["PCRE"] = False
        toolchain.cache_variables["GKREGEX"] = False
        toolchain.cache_variables["GKRAND"] = False
        toolchain.cache_variables["ASSERT"] = str(self.settings.build_type) == "Debug"
        toolchain.cache_variables["ASSERT2"] = False
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "2"])

    def package(self):
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["GKlib"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "GKlib")
        self.cpp_info.set_property("cmake_target_name", "GKlib::GKlib")
        self.cpp_info.set_property("pkg_config_name", "GKlib")
