#!/usr/bin/env python3
"""Conan recipe for aws-c-s3 0.13.2.

aws-c-s3 is an AWS S3 asynchronous client library focused on maximizing
throughput and network utilization.

Build system: CMake (C99 library).

Note: We use CMAKE_PREFIX_PATH instead of CMakeDeps because the aws-c-common
cmake config creates the AWS::aws-c-common target and adds CMake modules
(AwsCFlags, AwsCheckHeaders, etc.) to CMAKE_MODULE_PATH. CMakeDeps replaces
these with different target names (aws-c-common::aws-c-common) and doesn't
add the module path, causing build failures.

aws-c-s3 depends on aws-c-auth and aws-checksums (directly), and transitively
on aws-c-common, aws-c-cal, aws-c-io, aws-c-http, aws-c-sdkutils, and aws-lc.
All of these must be in CMAKE_PREFIX_PATH so find_package can locate their
cmake config files.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class AwsCs3Conan(ConanFile):
    name = "aws-c-s3"
    version = "0.13.2"
    description = "AWS S3 asynchronous client library (maximize throughput and network utilization)"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-s3"
    url = "https://github.com/awslabs/aws-c-s3"  # CI this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.14.3")
        self.requires("aws-c-io/0.27.5")
        self.requires("aws-c-http/0.11.0")
        self.requires("aws-c-cal/0.9.15")
        self.requires("aws-c-auth/0.10.4")
        self.requires("aws-checksums/0.2.10")
        self.requires("aws-c-sdkutils/0.2.7")
        # aws-lc is a transitive dep of aws-c-cal, but we need it as a direct
        # requirement so the Conan toolchain adds its lib/include paths to
        # CMAKE_LIBRARY_PATH/CMAKE_INCLUDE_PATH. This lets Findcrypto.cmake
        # (from aws-c-cal's cmake config) locate libcrypto.a and openssl headers.
        self.requires("aws-lc/5.4.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)

        # Use CMAKE_PREFIX_PATH to point to dependency package folders so that
        # find_package(aws-c-common) uses the original config file which:
        # 1. Creates the AWS::aws-c-common target (not aws-c-common::aws-c-common)
        # 2. Adds CMake modules (AwsCFlags, AwsCheckHeaders, etc.) to CMAKE_MODULE_PATH
        # 3. find_package(crypto) finds aws-lc's libcrypto via Findcrypto.cmake
        # Include all direct + transitive deps so find_dependency chains work.
        prefix_paths = []
        for dep_name in ["aws-c-common", "aws-c-cal", "aws-c-io",
                         "aws-c-http", "aws-c-auth", "aws-checksums",
                         "aws-c-sdkutils", "aws-lc", "aws-c-compression"]:
            try:
                dep = self.dependencies[dep_name]
                if dep.package_folder:
                    prefix_paths.append(dep.package_folder)
            except KeyError:
                pass  # transitive dep not directly required

        cmake.configure(variables={
            "CMAKE_PREFIX_PATH": ";".join(prefix_paths)
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["aws-c-s3"]
        self.cpp_info.set_property("cmake_file_name", "aws-c-s3")
        self.cpp_info.set_property("cmake_target_name", "aws-c-s3::aws-c-s3")
