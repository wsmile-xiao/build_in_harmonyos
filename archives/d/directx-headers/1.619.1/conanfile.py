#!/usr/bin/env python3
"""Conan recipe — directx-headers 1.619.1 (CMake)"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rmdir


class DirectXHeadersConan(ConanFile):
    name = "directx-headers"
    version = "1.619.1"
    description = "Official DirectX headers available under an open source license"
    license = "MIT"
    homepage = "https://github.com/microsoft/DirectX-Headers"
    url = "https://github.com/microsoft/DirectX-Headers"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["DXHEADERS_BUILD_TEST"] = False
        tc.cache_variables["DXHEADERS_BUILD_GOOGLE_TEST"] = False
        tc.cache_variables["DXHEADERS_INSTALL"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Remove CMake config files from package - consumers use Conan
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["DirectX-Headers", "DirectX-Guids"]
        # WSL stubs provide Windows compatibility headers (unknwn.h, rpc.h, etc.)
        # needed by winadapter.h on non-Windows platforms
        self.cpp_info.includedirs.append("include/wsl/stubs")
