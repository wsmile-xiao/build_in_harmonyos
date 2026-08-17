#!/usr/bin/env python3
"""Conan recipe for aws-c-sdkutils 0.2.7 — CMake build system.

aws-c-sdkutils provides AWS SDK utility functions (JSON parsing, endpoint
resolution, partition config, profile parsing).

Dependencies: aws-c-common/0.14.3
License: Apache-2.0

Note: AWS C libraries use custom CMake modules (AwsCFlags, AwsCheckHeaders, etc.)
and the AWS:: namespace for targets. These are provided by the aws-c-common
package's own CMake config (not by Conan's CMakeDeps generator). We use
CMAKE_PROJECT_TOP_LEVEL_INCLUDES to inject the dependency paths before the
project() command, so find_package(aws-c-common) finds the package's own
config which correctly exports AWS:: targets and adds cmake modules to
CMAKE_MODULE_PATH.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AwsCSdkutilsConan(ConanFile):
    name = "aws-c-sdkutils"
    version = "0.2.7"
    description = "AWS SDK utility functions: JSON parsing, endpoint resolution, partition config"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-sdkutils"
    url = "https://github.com/awslabs/aws-c-sdkutils"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared

        # AWS C libraries ship their own CMake config (aws-c-common-config.cmake)
        # which: (1) adds modules/ to CMAKE_MODULE_PATH, (2) creates AWS:: targets.
        # CMakeDeps would shadow this with aws-c-common::aws-c-common targets,
        # breaking the AWS CMakeLists.txt that expects AWS:: namespace.
        #
        # Solution: Use CMAKE_PROJECT_TOP_LEVEL_INCLUDES to inject a helper file
        # that appends dep_root to CMAKE_PREFIX_PATH and modules_dir to
        # CMAKE_MODULE_PATH. This runs during project() (before find_package),
        # so find_package(aws-c-common) finds the package's own config.
        dep = self.dependencies["aws-c-common"]
        dep_root = dep.package_folder
        if dep_root:
            modules_dir = os.path.join(
                dep_root, "lib", "cmake", "aws-c-common", "modules"
            )
            helper_path = os.path.join(self.generators_folder, "aws_paths.cmake")
            with open(helper_path, "w") as f:
                f.write(
                    f'list(APPEND CMAKE_PREFIX_PATH "{dep_root}")\n'
                    f'list(APPEND CMAKE_MODULE_PATH "{modules_dir}")\n'
                )
            tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = helper_path

        tc.generate()
        # Do NOT use CMakeDeps — we rely on the package's own CMake config

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["aws-c-sdkutils"]
        self.cpp_info.requires = ["aws-c-common::aws-c-common"]
