#!/usr/bin/env python3
"""Conan recipe — perlinnoise 3.0.0 (header-only)"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import cmake_layout


class PerlinNoiseConan(ConanFile):
    name = "perlinnoise"
    version = "3.0.0"
    description = "Perlin noise library for modern C++ (header-only, siv::PerlinNoise)"
    license = "MIT"
    homepage = "https://github.com/Reputeless/PerlinNoise"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32 平台检测：header-only 库理论平台无关，但仍遵守规程做白名单校验。
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "perlinnoise 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        # header-only：无编译步骤；此处统一应用 conandata 补丁（当前无补丁）
        apply_conandata_patches(self)

    def package(self):
        # 官方源码将 PerlinNoise.hpp 放在仓库根目录（无 include/ 子目录），
        # 安装到 include/ 供下游 #include <PerlinNoise.hpp> 使用。
        copy(
            self,
            "PerlinNoise.hpp",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
