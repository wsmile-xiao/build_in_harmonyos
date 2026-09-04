#!/usr/bin/env python3
"""Conan recipe — commata 1.3.1 (header-only C++17 CSV/TSV parser)"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import cmake_layout


class CommataConan(ConanFile):
    name = "commata"
    version = "1.3.1"
    description = "commata 1.3.1 — fast and flexible C++17 CSV/TSV parser (header-only)"
    license = "MIT"
    homepage = "https://github.com/furfurylic/commata"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32 平台检测：header-only 库理论平台无关，但仍遵守规程做白名单校验。
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "commata 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        # header-only：无编译步骤；此处统一应用 conandata 补丁
        apply_conandata_patches(self)

    def package(self):
        # 头文件位于 include/ 目录
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "*.natvis",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
