#!/usr/bin/env python3
"""Conan recipe revision 3.13.0.1 for GEOS 3.13.0 source.

GEOS is a C++ geometry engine with a stable C API used by geospatial
libraries such as GDAL, PROJ consumers, and MapServer. The OHOS package
builds static libgeos/libgeos_c plus the lightweight geosop CLI, while
running upstream CTest coverage and disabling only non-test auxiliary targets
such as benchmarks, website generation, and astyle.
"""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class GeosConan(ConanFile):
    name = "geos"
    version = "3.13.0.1"
    description = "Geometry Engine Open Source C/C++ geometry library"
    license = "LGPL-2.1-or-later"
    homepage = "https://libgeos.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

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
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = True
        tc.variables["BUILD_BENCHMARKS"] = False
        tc.variables["BUILD_WEBSITE"] = False
        tc.variables["BUILD_ASTYLE"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])
        if cross_building(self):
            self.output.info("cross-building: skip upstream CTest runtime execution")
            return
        self.run("ctest --output-on-failure --parallel 1", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "GEOS")
        self.cpp_info.set_property("pkg_config_name", "geos")
        self.cpp_info.libs = ["geos_c", "geos"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

        geos = self.cpp_info.components["geos"]
        geos.libs = ["geos"]
        geos.set_property("cmake_target_name", "GEOS::geos")
        if self.settings.os in ("Linux", "OHOS"):
            geos.system_libs = ["m"]

        geos_c = self.cpp_info.components["geos_c"]
        geos_c.libs = ["geos_c"]
        geos_c.requires = ["geos"]
        geos_c.set_property("cmake_target_name", "GEOS::geos_c")

        self.cpp_info.bindirs = ["bin"]
