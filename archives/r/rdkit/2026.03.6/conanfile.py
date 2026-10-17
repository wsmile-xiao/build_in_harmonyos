#!/usr/bin/env python3
"""Conan recipe - rdkit 2026.03.6 for HarmonyOS PC (arm64).

RDKit is a cheminformatics and machine learning toolkit written in C++.

Adaptation (OHOS):
- RDK_BUILD_PYTHON_WRAPPERS=OFF: no Python on OHOS CI
- RDK_BUILD_CPP_TESTS=OFF: disable C++ test suite
- CMAKE_SYSTEM_NAME=Linux: OHOS not recognized by CMake (E092),
  use Linux platform module (compiler still pointed to OHOS clang)
- RDK_INSTALL_INTREE=OFF: install to standard prefix layout
- Dependencies: boost/1.91.0.1, eigen/3.4.1, freetype/2.14.3,
  libpng/1.6.58.1, zlib/1.3.1.1
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
import os
import glob


class RdKitConan(ConanFile):
    name = "rdkit"
    version = "2026.03.6"
    description = "RDKit - cheminformatics and machine learning toolkit"
    license = "BSD-3-Clause"
    homepage = "https://github.com/rdkit/rdkit"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: settings.os must be checked with in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration
                (f"{self.ref} only supports Linux and OHOS platforms"
            )

    def requirements(self):
        self.requires("boost/1.91.0.1")
        self.requires("eigen/3.4.1")
        self.requires("freetype/2.14.3")
        self.requires("libpng/1.6.58.1")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # E092: CMake doesn't recognize HarmonyOS platform
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # R26: static build for system-name libs
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # OHOS adaptation: disable Python wrappers (no Python on OHOS CI)
        tc.variables["RDK_BUILD_PYTHON_WRAPPERS"] = "OFF"
        tc.variables["RDK_BUILD_CPP_TESTS"] = "OFF"
        tc.variables["RDK_BUILD_INCHI_SUPPORT"] = "OFF"
        tc.variables["RDK_BUILD_AVALON_SUPPORT"] = "OFF"
        tc.variables["RDK_BUILD_FREETYPE_SUPPORT"] = "ON"
        tc.variables["RDK_BUILD_DESCRIPTORS3D"] = "ON"
        tc.variables["RDK_BUILD_COORDGEN_SUPPORT"] = "ON"
        tc.variables["RDK_BUILD_MAPEARSER_SUPPORT"] = "ON"
        tc.variables["RDK_INSTALL_INTREE"] = "OFF"
        tc.variables["RDK_INSTALL_STATIC_LIBS"] = "ON"
        tc.variables["RDK_BUILD_THREEDSATATESSS"] = "ON"
        tc.variables["RDK_USE_BOOST_SERIALIZATION"] = "ON"
        tc.variables["RDK_USE_BOOST_IOSTREAMS"] = "ON"
        tc.variables["RDK_BUILD_SLN_SUPPORT"] = "ON"
        tc.variables["RDK_BUILD_CFFI_LIB"] = "OFF"
        tc.variables["RDK_BUILD_MINIMAL_LIB"] = "OFF"
        tc.variables["RDK_BUILD_YAEBMOMP_SUPPORT"] = "OFF"
        tc.variables["RDK_BUILD_XXZ2MOL_SUPPORT"] = "OFF"
        tc.variables["RDK_BUILD_STRUCTURECHECKER_SUPPORT"] = "OFF"
        tc.variables["RDK_BUILD_PUBCHEMSHAPE3D_SUPPORT"] = "ON"
        tc.variables["RDK_USE_URF"] = "ON"
        tc.variables["RDK_INSTALL_DEV_COMPONENT"] = "ON"
        tc.variables["RDK_USE_UNITY_BUILDS"] = "OFF"
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
        self.cpp_info.set_property("cmake_file_name", "RDKit")
        self.cpp_info.set_property("cmake_target_name", "RDKit::rdkit")
        self.cpp_info.set_property("pkg_config_name", "rdkit")

        # Auto-collect all installed libraries
        libdir = os.path.join(self.package_folder, "lib")
        libs = []
        if os.path.isdir(libdir):
            for f in sorted(glob.glob(os.path.join(libdir, "lib*.a"))):
                libname = os.path.basename(f)[3:-2]
                libs.append(libname)
            for f in sorted(glob.glob(os.path.join(libdir, "lib*.so"))):
                libname = os.path.basename(f)[3:-3]
                if libname not in libs:
                    libs.append(libname)
        self.cpp_info.libs = libs

        # rdkit installs headers to include/rdkit/
        self.cpp_info.includedirs = ["include/rdkit"]

        # Propagate dependencies to consumers
        self.cpp_info.requires = ["boost::boost", "eigen::eigen"]
