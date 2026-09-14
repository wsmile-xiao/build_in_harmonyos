#!/usr/bin/env python3
"""Conan recipe — simde 0.8.4-rc3 (header-only SIMD portability library).

simde（SIMD Everywhere）提供跨架构可移植 SIMD 头文件（simde/ 目录 472 个头文件），
上游 meson 只安装头文件、无编译产物，因此本配方按 header-library 打包 include 目录。

上游标签为 v0.8.4-rc3，项目内 meson 声明版本为 0.8.4（含 0.8.4 的全部 API 面），
配方版本严格取任务卡/目录/分支一致的 0.8.4-rc3。

上游测试：test/ 目录的 meson 注册入口在 OHOS aarch64 设备上全量执行（详见
test_package/MANIFEST.yml 与 notes.md）；所有注册入口均带 -DSIMDE_TEST_BARE，
不依赖 test/munit 子模块（官方 release tarball 中该子模块为空目录）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class SimdeConan(ConanFile):
    name = "simde"
    version = "0.8.4-rc3"
    package_type = "header-library"

    description = "SIMDe: portable SIMD intrinsics across architectures (header-only)"
    homepage = "https://github.com/simd-everywhere/simde"
    license = "MIT"
    url = "https://github.com/simd-everywhere/simde"
    topics = "simd", "header-only", "portability", "neon", "sse"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # header-only：无编译产物，仅应用补丁（当前 patches 为空，调用为 no-op）
        apply_conandata_patches(self)

    def package(self):
        copy(self, "simde/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "simde")
        self.cpp_info.set_property("cmake_target_name", "simde::simde")
        self.cpp_info.includedirs = ["include"]
        # header-only：显式声明无库产物（code-style 规则 4 要求 package_info 设置 libs）
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
