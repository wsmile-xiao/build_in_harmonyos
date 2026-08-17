#!/usr/bin/env python3
"""Conan recipe for vulkan-loader 1.3.295."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class VulkanLoaderConan(ConanFile):
    name = "vulkan-loader"
    version = "1.3.295"
    description = "Vulkan Loader - discovers and loads Vulkan ICDs and layers"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/Vulkan-Loader"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "vulkan-loader supports Linux and OHOS"
            )

    def requirements(self):
        self.requires("vulkan-headers/1.3.295")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Build shared library (libvulkan.so)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Disable all WSI (Window System Integration) support — OHOS is headless
        tc.variables["BUILD_WSI_XCB_SUPPORT"] = "OFF"
        tc.variables["BUILD_WSI_XLIB_SUPPORT"] = "OFF"
        tc.variables["BUILD_WSI_WAYLAND_SUPPORT"] = "OFF"
        tc.variables["BUILD_WSI_DIRECTFB_SUPPORT"] = "OFF"
        # Disable tests — not needed for the loader package
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.generate()
        # Generate CMakeDeps for vulkan-headers dependency
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["vulkan"]
        # Headers come from vulkan-headers, not this package
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "Vulkan")
        self.cpp_info.set_property("cmake_target_name", "Vulkan::Vulkan")
        self.cpp_info.set_property("pkg_config_name", "vulkan")
