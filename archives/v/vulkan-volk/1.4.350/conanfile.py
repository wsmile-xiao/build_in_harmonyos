#!/usr/bin/env python3
"""Conan recipe — vulkan-volk 1.4.350 (CMake static library).

volk is a meta-loader for Vulkan. It loads the Vulkan loader dynamically
at runtime and provides function pointers for all Vulkan entry points.

Built as a static library (libvolk.a) with volk.h header.
Patches add HarmonyOS platform support (Platform/HarmonyOS.cmake
and VK_USE_PLATFORM_OHOS auto-detection).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class VulkanVolkConan(ConanFile):
    name = "vulkan-volk"
    version = "1.4.350"
    description = (
        "Meta-loader for Vulkan API - loads Vulkan loader and provides "
        "function pointers for all Vulkan entry points"
    )
    license = "MIT"
    homepage = "https://github.com/zeux/volk"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: settings.os check uses in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "vulkan-volk supports Linux and OHOS only"
            )

    def requirements(self):
        self.requires("vulkan-headers/vulkan-sdk-1.4.357.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: volk is not a system-name library, static is fine
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # volk-specific CMake variables
        tc.variables["VOLK_INSTALL"] = True
        tc.variables["VOLK_PULL_IN_VULKAN"] = True
        # Point to vulkan-headers package for header discovery
        vh = self.dependencies["vulkan-headers"]
        tc.variables["VULKAN_HEADERS_INSTALL_DIR"] = vh.package_folder
        # R40: Set VK_USE_PLATFORM_OHOS for OHOS builds to enable
        # vulkan/vulkan_ohos.h inclusion through volk.h
        if self.settings.os == "OHOS":
            tc.variables["VOLK_STATIC_DEFINES"] = "VK_USE_PLATFORM_OHOS"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "volk")
        self.cpp_info.set_property("cmake_target_name", "volk::volk")
        self.cpp_info.libs = ["volk"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl"]
