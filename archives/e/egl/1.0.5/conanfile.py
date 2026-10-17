#!/usr/bin/env python3
"""Conan recipe for EGL 1.0.5 with an OHOS system-EGL backend."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class EglConan(ConanFile):
    name = "egl"
    version = "1.0.5"
    description = "Khronos EGL 1.5 desktop implementation with an OHOS system EGL forwarding backend"
    license = "MIT"
    homepage = "https://github.com/McNopper/EGL"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "egl/1.0.5 is only packaged for OHOS; use the upstream backend on other platforms."
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "egl/1.0.5 must be static to avoid colliding with /system/lib64/libEGL.so."
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        # Codeload tag URLs end in the tag name rather than an archive extension.
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
            filename="egl-1.0.5.tar.gz",
        )

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = "OFF"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "libEGL.a",
            dst=os.path.join(self.package_folder, "lib"),
            src=os.path.join(self.source_folder, "lib"),
        )
        for subdirectory in ("EGL", "KHR"):
            copy(
                self,
                "*.h",
                dst=os.path.join(self.package_folder, "include", subdirectory),
                src=os.path.join(self.source_folder, "include", subdirectory),
            )

    def package_info(self):
        self.cpp_info.libs = ["EGL"]
        self.cpp_info.includedirs = ["include", "include/EGL", "include/KHR"]
        self.cpp_info.set_property("cmake_file_name", "EGL")
        self.cpp_info.set_property("cmake_target_name", "EGL::EGL")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl"]
