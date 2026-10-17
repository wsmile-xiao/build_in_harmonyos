#!/usr/bin/env python3
"""Conan recipe for aws-checksums 0.2.10.

aws-checksums provides efficient checksum computation (CRC32, CRC32C,
CRC64-NVME, XXHash) with ARM NEON SIMD acceleration on aarch64.

Build system: CMake (C99 library, depends on aws-c-common).
"""

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class AwsChecksumsConan(ConanFile):
    name = "aws-checksums"
    version = "0.2.10"
    description = "AWS efficient checksum library — CRC32/CRC32C/CRC64/XXHash with NEON SIMD"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-checksums"
    url = "https://github.com/awslabs/aws-checksums"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.14.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

        # aws-checksums CMakeLists.txt calls find_package(aws-c-common REQUIRED)
        # and includes AWS CMake modules (AwsSIMD, AwsCFlags, etc.) that are
        # installed by aws-c-common. CMakeDeps generates the config file but
        # does not add the modules directory to CMAKE_MODULE_PATH.
        deps = CMakeDeps(self)
        deps.set_property("aws-c-common", "cmake_target_name", "AWS::aws-c-common")
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Pass aws-c-common's CMake modules directory so that include(AwsSIMD)
        # etc. in the CMakeLists.txt can find them.
        aws_common = self.dependencies["aws-c-common"]
        modules_dir = os.path.join(
            aws_common.package_folder,
            "lib", "cmake", "aws-c-common", "modules",
        )
        cmake.configure(variables={"CMAKE_MODULE_PATH": modules_dir})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["aws-checksums"]
        # R32: settings.os judgment must use "in" for OHOS compatibility
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl"]
