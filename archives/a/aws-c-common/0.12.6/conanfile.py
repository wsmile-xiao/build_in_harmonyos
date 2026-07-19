#!/usr/bin/env python3
"""Conan recipe for aws-c-common 0.12.6 — AWS SDK for C core library.

Provides cross-platform abstractions (memory, strings, lists, hash tables, threads, etc.).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AwsccommonConan(ConanFile):
    name = "aws-c-common"
    version = "0.12.6"
    description = "AWS SDK for C 核心基础库，提供跨平台抽象层（内存、字符串、列表、哈希表、线程等）"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-common"
    url = "https://github.com/awslabs/aws-c-common"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["aws-c-common"]
