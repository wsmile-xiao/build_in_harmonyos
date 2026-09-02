#!/usr/bin/env python3
"""Conan recipe for svt-av1 4.1.0 — SVT-AV1 AV1 video encoder library."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class SvtAv1Conan(ConanFile):
    name = "svt-av1"
    version = "4.1.0"
    description = "Scalable Video Technology for AV1 — high-performance AV1 encoder"
    license = "BSD-3-Clause"
    homepage = "https://gitlab.com/AOMediaCodec/SVT-AV1"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN/../lib"
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"
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
        self.cpp_info.set_property("cmake_file_name", "SvtAv1Enc")
        self.cpp_info.set_property("cmake_target_name", "SvtAv1Enc::SvtAv1Enc")
        self.cpp_info.set_property("pkg_config_name", "SvtAv1Enc")
        self.cpp_info.libs = ["SvtAv1Enc"]
        self.cpp_info.includedirs = ["include"]
