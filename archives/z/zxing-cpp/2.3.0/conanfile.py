#!/usr/bin/env python3
"""Conan recipe for zxing-cpp 2.3.0."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class ZxingCppConan(ConanFile):
    name = "zxing-cpp"
    version = "2.3.0"
    description = "C++ barcode scanning and generation library"
    license = "Apache-2.0"
    homepage = "https://github.com/zxing-cpp/zxing-cpp"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

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
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_CXX_STANDARD"] = 17
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.variables["CMAKE_CXX_EXTENSIONS"] = False
        tc.variables["ZXING_EXAMPLES"] = False
        tc.variables["ZXING_C_API"] = False
        tc.variables["ZXING_UNIT_TESTS"] = False
        tc.variables["ZXING_BLACKBOX_TESTS"] = False
        tc.variables["ZXING_PYTHON_MODULE"] = False
        tc.variables["ZXING_USE_BUNDLED_ZINT"] = True
        tc.variables["ZXING_DEPENDENCIES"] = "AUTO"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=self.package_folder + "/licenses")
        # The upstream pkg-config template bakes CMAKE_INSTALL_PREFIX into
        # libdir/includedir.  Make the package relocatable in the Conan cache
        # and in downstream installations.
        save(
            self,
            os.path.join(self.package_folder, "lib", "pkgconfig", "zxing.pc"),
            """libdir=${pcfiledir}/..
includedir=${pcfiledir}/../..

Name: ZXing
Description: ZXing-C++ library
Version: 2.3.0
Libs: -L${libdir} -lZXing
Cflags: -I${includedir} -I${includedir}/ZXing
""",
        )

    def package_info(self):
        self.cpp_info.libs = ["ZXing"]
        self.cpp_info.set_property("cmake_file_name", "ZXing")
        self.cpp_info.set_property("cmake_target_name", "ZXing::ZXing")
        self.cpp_info.set_property("pkg_config_name", "zxing")
