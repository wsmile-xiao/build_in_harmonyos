#!/usr/bin/env python3
"""Conan recipe — aws-c-cal 0.9.15 (CMake).

aws-c-cal is AWS Crypto Abstraction Layer providing hash, HMAC, RSA, ECDH
and symmetric cipher interfaces. It uses aws-lc as the crypto backend.

Note: We use CMAKE_PREFIX_PATH instead of CMakeDeps because the aws-c-common
cmake config creates the AWS::aws-c-common target and adds CMake modules
(AwsCFlags, etc.) to CMAKE_MODULE_PATH. CMakeDeps replaces these with
different target names (aws-c-common::aws-c-common) and doesn't add the
module path, causing build failures.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AwsccalConan(ConanFile):
    name = "aws-c-cal"
    version = "0.9.15"
    description = "AWS Crypto Abstraction Layer (CAL) - hash, HMAC, RSA, ECDH, symmetric cipher"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-cal"
    url = "https://github.com/awslabs/aws-c-cal"  # CI this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.14.3")
        self.requires("aws-lc/5.4.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["USE_OPENSSL"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)

        # Use CMAKE_PREFIX_PATH to point to dependency package folders so that
        # find_package(aws-c-common) uses the original config file which:
        # 1. Creates the AWS::aws-c-common target (not aws-c-common::aws-c-common)
        # 2. Adds CMake modules (AwsCFlags, etc.) to CMAKE_MODULE_PATH
        # 3. find_package(crypto) finds aws-lc's libcrypto via Findcrypto.cmake
        prefix_paths = []
        for dep_name in ["aws-c-common", "aws-lc"]:
            dep = self.dependencies[dep_name]
            prefix_paths.append(dep.package_folder)
        cmake.configure(variables={
            "CMAKE_PREFIX_PATH": ";".join(prefix_paths)
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["aws-c-cal"]
        self.cpp_info.set_property("cmake_file_name", "aws-c-cal")
        self.cpp_info.set_property("cmake_target_name", "aws-c-cal::aws-c-cal")
