#!/usr/bin/env python3
"""Conan recipe for vulkan-headers 1.3.295."""
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


class VulkanHeadersConan(ConanFile):
    name = "vulkan-headers"
    version = "1.3.295"
    description = "Vulkan Header files and API registry"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/Vulkan-Headers"
    url = ""

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "vulkan-headers supports Linux/OHOS/FreeBSD/Macos/Windows"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.install()

    def package(self):
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # Re-run install to package folder
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "VulkanHeaders")
        self.cpp_info.set_property("cmake_target_name", "Vulkan::Headers")
        self.cpp_info.set_property("pkg_config_name", "VulkanHeaders")

    def package_id(self):
        self.info.clear()
