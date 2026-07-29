#!/usr/bin/env python3
"""Conan recipe for SPIRV-Cross vulkan-sdk-1.4.341.0."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class SpirvCrossConan(ConanFile):
    name = "spirv-cross"
    version = "1.4.341.0"
    description = "SPIR-V reflection and cross-compilation library and CLI"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/SPIRV-Cross"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("spirv-cross is supported on Linux and OHOS")
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "This package keeps the static libraries required by the spirv-cross CLI"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["SPIRV_CROSS_SHARED"] = False
        toolchain.variables["SPIRV_CROSS_STATIC"] = True
        toolchain.variables["SPIRV_CROSS_CLI"] = True
        toolchain.variables["SPIRV_CROSS_ENABLE_TESTS"] = True
        toolchain.variables["SPIRV_CROSS_FORCE_PIC"] = self.options.fPIC
        toolchain.variables["SPIRV_CROSS_WERROR"] = False
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
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
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = [
            "spirv-cross-c",
            "spirv-cross-cpp",
            "spirv-cross-reflect",
            "spirv-cross-msl",
            "spirv-cross-hlsl",
            "spirv-cross-glsl",
            "spirv-cross-util",
            "spirv-cross-core",
        ]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
