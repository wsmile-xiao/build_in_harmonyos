#!/usr/bin/env python3
"""Conan recipe — fastnoiselite 1.1.1 (header-only)"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FastnoiseliteConan(ConanFile):
    name = "fastnoiselite"
    version = "1.1.1"
    description = "FastNoiseLite: single-file portable noise generation library for C++"
    license = "MIT"
    homepage = "https://github.com/Auburn/FastNoiseLite"
    url = "https://github.com/Auburn/FastNoiseLite"

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32 平台检测：header-only 理论平台无关，仍按规程做白名单校验。
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "fastnoiselite 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self)

    def build(self):
        # header-only：无编译步骤（不得伪造编译日志 — R34），统一应用 conandata 补丁（当前无补丁）
        apply_conandata_patches(self)

    def package(self):
        # 官方源码将头文件放在 Cpp/ 子目录，安装到 include/ 供下游
        # #include <FastNoiseLite.h> 使用。
        copy(
            self,
            "FastNoiseLite.h",
            src=os.path.join(self.source_folder, "Cpp"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
