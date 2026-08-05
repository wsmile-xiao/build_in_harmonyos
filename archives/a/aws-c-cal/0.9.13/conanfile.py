#!/usr/bin/env python3
"""Conan recipe for aws-c-cal 0.9.13 — AWS Crypto Abstraction Layer.

Provides HMAC, block cipher, hash, RSA, ECDH and other cryptographic
function interfaces. Uses aws-lc as the crypto backend.

R26: System-name libraries (libcrypto/libssl) are static in the aws-lc
dependency recipe. This recipe also defaults to static.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class AwsccalConan(ConanFile):
    name = "aws-c-cal"
    version = "0.9.13"
    description = "AWS Crypto Abstraction Layer — HMAC, block cipher, hash, RSA, ECDH"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-cal"
    url = "https://github.com/awslabs/aws-c-cal"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.12.6")
        self.requires("aws-lc/5.4.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

        # aws-c-cal CMakeLists.txt calls find_package(crypto REQUIRED),
        # expecting an AWS::crypto target. aws-lc's Conan package name is
        # "aws-lc", so CMakeDeps would normally generate aws-lc-config.cmake.
        # We override the cmake_file_name and cmake_target_name so that
        # find_package(crypto) resolves correctly.
        deps = CMakeDeps(self)
        deps.set_property("aws-lc", "cmake_file_name", "crypto")
        deps.set_property("aws-lc", "cmake_target_name", "AWS::crypto")
        # aws-c-cal's AwsFindPackage module expects AWS::aws-c-common target,
        # not the default aws-c-common::aws-c-common.
        deps.set_property("aws-c-common", "cmake_target_name", "AWS::aws-c-common")
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # aws-c-common installs CMake helper modules (AwsCFlags, AwsFindPackage,
        # etc.) to lib/cmake/aws-c-common/modules/. The aws-c-cal CMakeLists.txt
        # includes these modules. CMakeDeps generates its own config file that
        # does not add this directory to CMAKE_MODULE_PATH. We pass it as a -D
        # variable so that the CMakeDeps list(PREPEND ...) block picks it up
        # from the cache variable and preserves it in the normal variable.
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
        self.cpp_info.libs = ["aws-c-cal"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "rt"]
