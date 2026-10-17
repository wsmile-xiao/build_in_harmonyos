#!/usr/bin/env python3
"""Conan recipe for cmake-extras — 纯 CMake 模块集合数据包。

cmake-extras 是 Lomiri/UBports 生态的 CMake 附加模块集合（src/ 下
CopyrightTest / CoverageReport / DoxygenBuilder / FormatCode / GDbus /
GMock / GObjectIntrospection / GSettings / GdbusCodegen / IncludeChecker /
Intltool / Lcov / QmlPlugins / Vala / gcovr 等），无原生编译——CMakeLists.txt
仅把 src/ 目录安装到 ${DATADIR}/cmake/（find_package config 机制）。
纯数据包，package() 拷贝模块目录即可。R34 校验共享目录内模块文件存在。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class CmakeExtrasConan(ConanFile):
    name = "cmake-extras"
    version = "1.9"
    package_type = "application"
    license = "GPL-3.0-only"
    homepage = "https://gitlab.com/ubports/development/core/cmake-extras"
    description = "cmake-extras — Lomiri/UBports CMake 附加模块集合（纯 CMake 模块，无编译）"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"cmake-extras does not support os={self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯数据包——无编译
        apply_conandata_patches(self)  # 无补丁时空操作

    def package(self):
        # 拷贝 src/ 下所有 CMake 模块目录到 share/cmake/
        src_dir = os.path.join(self.source_folder, "src")
        if not os.path.isdir(src_dir):
            raise ConanInvalidConfiguration(f"src/ not found in source: {src_dir}")
        dst_dir = os.path.join(self.package_folder, "share", "cmake")
        os.makedirs(dst_dir, exist_ok=True)
        for name in os.listdir(src_dir):
            s = os.path.join(src_dir, name)
            if os.path.isdir(s):
                d = os.path.join(dst_dir, name)
                if not os.path.exists(d):
                    shutil.copytree(s, d)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
