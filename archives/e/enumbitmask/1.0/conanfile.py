#!/usr/bin/env python3
"""Conan recipe — enumbitmask 1.0 (header-only)

EnumBitmask 1.0（https://github.com/Reputeless/EnumBitmask）：
单头文件 C++17 库，为 enum class 类型启用位掩码运算符
（& | ^ ~ &= |= ^=，constexpr，CC0-1.0 许可）。无构建系统，
无编译产物，仅打包头文件与许可证。依赖：0。
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class EnumbitmaskConan(ConanFile):
    name = "enumbitmask"
    version = "1.0"
    description = ("EnumBitmask: enable bitmask operators for enum class types "
                   "(header-only C++17 library)")
    license = "CC0-1.0"
    homepage = "https://github.com/Reputeless/EnumBitmask"
    url = "https://github.com/Reputeless/EnumBitmask"

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32 平台检测：header-only 理论平台无关，仍按规程做白名单校验。
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "enumbitmask 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(
                    self.settings.os))

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self)

    def build(self):
        # header-only：无编译步骤（不得伪造编译日志 — R34），统一应用 conandata 补丁（当前无补丁）
        apply_conandata_patches(self)

    def package(self):
        # 官方源码将头文件放在仓库根目录，安装到 include/ 供下游
        # #include <EnumBitmask.hpp> 使用。
        copy(
            self,
            "EnumBitmask.hpp",
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

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
