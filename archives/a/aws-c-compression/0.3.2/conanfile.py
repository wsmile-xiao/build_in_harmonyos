#!/usr/bin/env python3
"""Conan recipe for aws-c-compression 0.3.2 — AWS C Huffman encoding/decoding library.

Provides Huffman coding for HTTP/2 HPACK compression.
Depends on aws-c-common for core platform abstractions.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class AwsccompressionConan(ConanFile):
    name = "aws-c-compression"
    version = "0.3.2"
    description = "AWS C SDK compression library providing Huffman encoding/decoding for HTTP/2 HPACK"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-compression"
    url = "https://github.com/awslabs/aws-c-compression"

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

        # AWS C SDK uses custom CMake modules (AwsCFlags, AwsSharedLibSetup, etc.)
        # from aws-c-common, and AWS:: target namespace. CMakeDeps generates its
        # own config that doesn't include CMAKE_MODULE_PATH or AWS:: namespace.
        # Append aws-c-common package dir to CMAKE_PREFIX_PATH so find_package
        # finds the upstream config which sets CMAKE_MODULE_PATH + AWS:: targets.
        aws_common = self.dependencies["aws-c-common"]
        toolchain_file = os.path.join(self.generators_folder,
                                      "conan_toolchain.cmake")
        with open(toolchain_file, "a") as f:
            f.write("\n# aws-c-compression: use upstream aws-c-common "
                    "config (AWS:: namespace + custom modules)\n")
            f.write(f'list(APPEND CMAKE_PREFIX_PATH '
                    f'"{aws_common.package_folder}")\n')

        # Workaround: CI worker's lld linker can't find libxml2.so.16
        # The library is in the llvm/lib directory but not in LD_LIBRARY_PATH
        for lib in glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib/libxml2.so*"):
            lib_dir = os.path.dirname(lib)
            build_env = os.path.join(self.generators_folder, "conanbuild.sh")
            with open(build_env, "a") as f:
                f.write(f'\nexport LD_LIBRARY_PATH="{lib_dir}:$LD_LIBRARY_PATH"\n')
            break

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["aws-c-compression"]
