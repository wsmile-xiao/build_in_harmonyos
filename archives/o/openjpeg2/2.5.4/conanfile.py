#!/usr/bin/env python3
"""Conan recipe for OpenJPEG 2.5.4 core libopenjp2 library."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class OpenJpeg2Conan(ConanFile):
    name = "openjpeg2"
    version = "2.5.4"
    description = "Open-source JPEG 2000 codec library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/uclouvain/openjpeg"
    url = "https://github.com/uclouvain/openjpeg"
    package_type = "library"

    exports_sources = "patches/*"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "thread": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "thread": True,
    }

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["OPENJPEG_NO_VERSIONED_SONAME"] = True

        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_STATIC_LIBS"] = not bool(self.options.shared)
        tc.variables["BUILD_CODEC"] = False
        tc.variables["BUILD_DOC"] = False
        tc.variables["BUILD_JAVA"] = False
        tc.variables["BUILD_JPIP"] = False
        tc.variables["BUILD_LUTS_GENERATOR"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_UNIT_TESTS"] = str(self.settings.os) in (
            "Linux",
            "OHOS",
        )
        tc.variables["OPENJPEG_BUILD_CORE_TESTS"] = str(
            self.settings.os
        ) in ("Linux", "OHOS")
        tc.variables["BUILD_VIEWER"] = False
        tc.variables["OPJ_USE_THREAD"] = bool(self.options.thread)
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        if str(self.settings.os) == "OHOS":
            self.conf.define("tools.build:jobs", 1)
        cmake.build()
        if str(self.settings.os) in ("Linux", "OHOS"):
            cmake.ctest(cli_args=["--output-on-failure"])
            unit_test_dir = os.path.join(self.build_folder, "bin")
            self.run(
                '"{}"'.format(
                    os.path.join(unit_test_dir, "test_sparse_array")
                )
            )
            self.run(
                '"{}" -size 256 -offset 127 127 '
                "-num_resolutions 6 -check".format(
                    os.path.join(unit_test_dir, "bench_dwt")
                )
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["openjp2"]
        self.cpp_info.includedirs = ["include/openjpeg-2.5"]
        self.cpp_info.set_property("cmake_file_name", "openjpeg2")
        self.cpp_info.set_property("cmake_target_name", "openjpeg2::openjpeg2")
        self.cpp_info.set_property("pkg_config_name", "libopenjp2")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
        if not self.options.shared:
            self.cpp_info.defines.append("OPJ_STATIC")
