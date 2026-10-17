#!/usr/bin/env python3
"""Conan recipe for aws-c-http 0.11.0.

aws-c-http is AWS SDK for C HTTP/1.1 and HTTP/2 client/server library,
supporting multiplexing, connection pooling, and WebSocket.

Build system: CMake (C99 library).

Note: We use CMAKE_PREFIX_PATH instead of CMakeDeps because the aws-c-common
cmake config creates the AWS::aws-c-common target and adds CMake modules
(AwsCFlags, AwsCheckHeaders, etc.) to CMAKE_MODULE_PATH. CMakeDeps replaces
these with different target names (aws-c-common::aws-c-common) and doesn't
add the module path, causing build failures.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class AwsCHttpConan(ConanFile):
    name = "aws-c-http"
    version = "0.11.0"
    description = "AWS SDK for C HTTP/1.1 and HTTP/2 client/server library (multiplexing, connection pooling, WebSocket)"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-http"
    url = "https://github.com/awslabs/aws-c-http"  # CI this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.14.3")
        self.requires("aws-c-io/0.27.5")
        self.requires("aws-c-compression/0.3.2")
        self.requires("aws-c-cal/0.9.15")
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
        # aws-lc is a transitive dep of aws-c-cal; its package folder must be
        # in CMAKE_PREFIX_PATH so Findcrypto.cmake can locate libcrypto.
        prefix_paths = []
        for dep_name in ["aws-c-common", "aws-c-io", "aws-c-compression",
                         "aws-c-cal", "aws-lc"]:
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
        self.cpp_info.libs = ["aws-c-http"]
        self.cpp_info.set_property("cmake_file_name", "aws-c-http")
        self.cpp_info.set_property("cmake_target_name", "aws-c-http::aws-c-http")
