#!/usr/bin/env python3
"""Conan recipe — opencl-headers 2026.05.29 (header-only)"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.cmake import cmake_layout


class OpenclHeadersConan(ConanFile):
    name = "opencl-headers"
    version = "2026.05.29"
    description = "C language header files for the OpenCL API (Khronos Group)"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/OpenCL-Headers"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def configure(self):
        # R32 平台检测：header-only 库理论平台无关，但仍遵守规程做白名单校验。
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "opencl-headers 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        # header-only：无编译步骤
        pass

    def package(self):
        # OpenCL-Headers 源码的 CL/ 目录下即所有公开头文件，安装到 include/CL/。
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "CL"),
            dst=os.path.join(self.package_folder, "include", "CL"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
