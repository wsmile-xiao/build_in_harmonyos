#!/usr/bin/env python3
"""Conan recipe — utf8proc 2.11.3 (CMake)"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Utf8ProcConan(ConanFile):
    name = "utf8proc"
    version = "2.11.3"
    description = "Clean C library for processing UTF-8 Unicode data"
    license = "MIT"
    homepage = "https://github.com/JuliaStrings/utf8proc"
    url = "https://github.com/JuliaStrings/utf8proc"

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

        # Fix: lld linker in OHOS SDK needs libxml2.so.16 at runtime.
        # The SDK lib directory is not in LD_LIBRARY_PATH on CI workers.
        env = Environment()
        for sdk_lib in glob.glob(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
        ):
            env.append("LD_LIBRARY_PATH", sdk_lib)
        envvars = env.vars(self)
        envvars.save_script("utf8proc_env")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["utf8proc"]
