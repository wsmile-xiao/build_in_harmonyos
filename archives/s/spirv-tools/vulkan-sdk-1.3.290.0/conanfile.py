#!/usr/bin/env python3
"""Conan recipe for SPIRV-Tools vulkan-sdk-1.3.290.0."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SpirvToolsConan(ConanFile):
    name = "spirv-tools"
    version = "vulkan-sdk-1.3.290.0"
    description = "Tools and libraries for processing SPIR-V modules"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/SPIRV-Tools"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("spirv-tools supports Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"]["main"], strip_root=True)
        headers_dir = os.path.join(self.source_folder, "external", "spirv-headers")
        os.makedirs(headers_dir, exist_ok=True)
        get(
            self,
            **self.conan_data["sources"]["spirv_headers"],
            destination=headers_dir,
            strip_root=True,
        )
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.fPIC
        tc.variables["SPIRV_SKIP_TESTS"] = False
        tc.variables["SPIRV_WERROR"] = False
        tc.variables["SPIRV_TOOLS_BUILD_STATIC"] = True
        tc.variables["ENABLE_SPIRV_TOOLS_INSTALL"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self.run(
                f'ctest --test-dir "{self.build_folder}" --output-on-failure -j1'
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["SPIRV-Tools"]
        self.cpp_info.set_property("cmake_file_name", "spirv-tools")
        self.cpp_info.set_property("cmake_target_name", "spirv-tools::spirv-tools")
        self.cpp_info.system_libs = ["m"] if self.settings.os == "OHOS" else ["m", "pthread"]
