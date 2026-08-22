#!/usr/bin/env python3
"""Conan recipe for swift-corelibs-blocksruntime 6.3.3."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SwiftCorelibsBlocksRuntimeConan(ConanFile):
    name = "swift-corelibs-blocksruntime"
    version = "6.3.3"
    description = "Runtime support for the C and Objective-C Blocks feature"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://github.com/swiftlang/swift-corelibs-blocksruntime"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "swift-corelibs-blocksruntime supports Linux and OHOS"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        tc.variables["CMAKE_BUILD_TYPE"] = str(self.settings.build_type)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["BlocksRuntime"]
        self.cpp_info.includedirs = ["include/BlocksRuntime"]
        self.cpp_info.set_property("cmake_file_name", "BlocksRuntime")
        self.cpp_info.set_property("cmake_target_name", "BlocksRuntime::BlocksRuntime")
