#!/usr/bin/env python3
"""Conan recipe — ifcplusplus 2.5 (ifcquery/ifcplusplus), library package.

IFC++ is an open source C++ library for reading and writing Industry
Foundation Classes (IFC) STEP files. This recipe builds the static
IfcPlusPlus library only (demo CLI applications are not packaged),
with all bundled third-party sources (Carve, RapidJSON, earcut, glm,
nowide, utf8, zippy) compiled in.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class IfcplusplusConan(ConanFile):
    name = "ifcplusplus"
    version = "2.5"
    description = "IFC++ - open source C++ library for IFC (Industry Foundation Classes) models"
    license = "MIT"
    homepage = "https://github.com/ifcquery/ifcplusplus"
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
        # Library package: do not build the demo CLI/viewer applications.
        tc.variables["BUILD_CONSOLE_APPLICATION"] = "OFF"
        tc.variables["BUILD_VIEWER_APPLICATION"] = "OFF"
        # E092: CMake does not recognize OHOS, inject Linux platform + armv8
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "armv8"
        # CMake 4.x compatibility: upstream cmake_minimum_required(3.6) needs
        # an explicit policy floor on newer CMake versions.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream installs the static library into bin/ (ARCHIVE DESTINATION
        # bin) — normalize it to the Conan convention lib/.
        bindir = os.path.join(self.package_folder, "bin")
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(bindir):
            os.makedirs(libdir, exist_ok=True)
            for name in os.listdir(bindir):
                if name.endswith(".a"):
                    shutil.move(os.path.join(bindir, name), os.path.join(libdir, name))

    def package_info(self):
        self.cpp_info.libs = ["IfcPlusPlus"]