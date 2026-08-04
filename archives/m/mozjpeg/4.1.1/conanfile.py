#!/usr/bin/env python3
"""Conan recipe for mozjpeg 4.1.1 on OpenHarmony."""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
import os


class MozjpegConan(ConanFile):
    name = "mozjpeg"
    version = "4.1.1"
    package_type = "library"
    license = "BSD-3-Clause AND IJG AND Zlib"
    homepage = "https://github.com/mozilla/mozjpeg"
    description = "JPEG codec with improved compression quality"
    topics = ("jpeg", "image", "codec", "compression")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "mozjpeg/4.1.1 is adapted and validated for OHOS/armv8 only."
            )

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("libpng/1.6.58")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        toolchain.variables["ENABLE_SHARED"] = self.options.shared
        toolchain.variables["ENABLE_STATIC"] = True
        toolchain.variables["PNG_SUPPORTED"] = True
        toolchain.variables["WITH_SIMD"] = False
        toolchain.variables["WITH_JAVA"] = False
        toolchain.variables["WITH_FUZZ"] = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(
            variables={
                "CMAKE_POLICY_VERSION_MINIMUM": "3.12",
            }
        )
        cmake.build()
        cmake.test()

    def package(self):
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["jpeg", "turbojpeg"]
        self.cpp_info.requires = ["zlib::zlib", "libpng::libpng"]
        self.cpp_info.set_property("cmake_file_name", "mozjpeg")
        self.cpp_info.set_property("cmake_target_name", "mozjpeg::mozjpeg")
        self.cpp_info.set_property("pkg_config_name", "libjpeg")
