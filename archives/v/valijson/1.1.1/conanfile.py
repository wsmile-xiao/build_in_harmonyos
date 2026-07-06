#!/usr/bin/env python3
"""Conan recipe — valijson 1.1.1 (CMake header-only library).

valijson is a header-only C++ library for JSON Schema validation.
It uses CMake with INTERFACE library target (no compilation needed).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ValijsonConan(ConanFile):
    name = "valijson"
    version = "1.1.1"
    description = "Header-only C++ library for JSON Schema validation"
    license = "BSD-2-Clause"
    homepage = "https://github.com/tristanpenman/valijson"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()
        
        # Fix compiler paths if profile's paths don't exist locally
        cc = shutil.which("clang") or "clang"
        cxx = shutil.which("clang++") or "clang++"
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.exists(toolchain_file):
            with open(toolchain_file, "r") as f:
                content = f.read()
            # Replace any compiler paths in the toolchain file
            import re
            content = re.sub(
                r'set\(CMAKE_C_COMPILER\s+"[^"]+"\)',
                f'set(CMAKE_C_COMPILER "{cc}")',
                content
            )
            content = re.sub(
                r'set\(CMAKE_CXX_COMPILER\s+"[^"]+"\)',
                f'set(CMAKE_CXX_COMPILER "{cxx}")',
                content
            )
            with open(toolchain_file, "w") as f:
                f.write(content)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
