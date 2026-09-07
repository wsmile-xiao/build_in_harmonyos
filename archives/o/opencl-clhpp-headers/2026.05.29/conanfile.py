#!/usr/bin/env python3
"""Conan recipe — opencl-clhpp-headers 2026.05.29 (header-only)"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OpenclClhppHeadersConan(ConanFile):
    name = "opencl-clhpp-headers"
    version = "2026.05.29"
    description = "C++ API header files for the OpenCL API (Khronos Group)"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/OpenCL-CLHPP"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "opencl-clhpp-headers only supports Linux/OHOS/FreeBSD/Macos/Windows, current: {}".format(self.settings.os))

    def requirements(self):
        self.requires("opencl-headers/2026.05.29")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)  # no patches currently

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include", "CL"),
             dst=os.path.join(self.package_folder, "include", "CL"))
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
