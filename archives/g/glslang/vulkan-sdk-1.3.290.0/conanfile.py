#!/usr/bin/env python3
"""Conan recipe for glslang vulkan-sdk-1.3.290.0."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
)


class GlslangConan(ConanFile):
    name = "glslang"
    version = "vulkan-sdk-1.3.290.0"
    description = "Khronos reference front end and validator for GLSL and ESSL"
    license = "BSD-3-Clause"
    homepage = "https://github.com/KhronosGroup/glslang"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("glslang supports Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.fPIC
        tc.variables["BUILD_TESTING"] = True
        tc.variables["GLSLANG_TESTS"] = True
        tc.variables["ENABLE_GLSLANG_BINARIES"] = True
        tc.variables["ENABLE_HLSL"] = True
        tc.variables["ENABLE_OPT"] = False
        tc.variables["ALLOW_EXTERNAL_SPIRV_TOOLS"] = False
        tc.variables["ENABLE_SPVREMAPPER"] = True
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
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # This tag folds HLSL sources into MachineIndependent; it installs no HLSL library.
        preferred = [
            "glslang",
            "SPIRV",
            "SPVRemapper",
            "MachineIndependent",
            "OSDependent",
            "GenericCodeGen",
        ]
        installed = collect_libs(self)
        self.cpp_info.libs = [name for name in preferred if name in installed]
        self.cpp_info.libs.extend(name for name in installed if name not in preferred)
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "glslang")
        self.cpp_info.set_property("cmake_target_name", "glslang::glslang")
        self.cpp_info.system_libs = ["m"] if self.settings.os == "OHOS" else ["m", "pthread"]
