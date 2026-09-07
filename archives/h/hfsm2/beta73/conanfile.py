#!/usr/bin/env python3
"""Conan recipe — hfsm2 Beta73 (header-only, CMake INTERFACE).

hfsm2 是 header-only 的分层状态机库（C++14+），上游以 include/hfsm2/*.hpp 交付，
无编译产物、无 configure/make 构建入口。OHOS PC 上直接打包 include/hfsm2/ 全部
头文件即可，无任何系统依赖（R39 官方源 URL + SHA-256 校验）。
Conan 2 要求 name/version 全小写 slug（上游 tag 为 Beta73，归档目录/配方版本用 beta73）。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.layout import basic_layout


class Hfsm2Conan(ConanFile):
    name = "hfsm2"
    version = "beta73"
    description = "HFSM2 - Lightweight, header-only C++14 hierarchical state machine framework."
    license = "MIT"
    homepage = "https://github.com/andrew-gresyk/HFSM2"
    url = "https://github.com/andrew-gresyk/HFSM2"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：无编译产物，无 configure/make 入口
        # 应用 conandata.yml 声明的补丁（本库 patches 为空，无实际应用；G1 配方完整性要求此调用）
        apply_conandata_patches(self)

    def package(self):
        # header-only：分发 include/hfsm2/ 全部头文件（machine.hpp / machine_dev.hpp / detail/）
        # 注意：copy() 的 src 为 include/，模式需相对该目录用 hfsm2/*（不能用 include/hfsm2/*）
        copy(self, "hfsm2/*", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        # 与上游 include 用法对齐：hfsm2::hfsm2（consumers 用 find_package(hfsm2)）
        self.cpp_info.set_property("cmake_file_name", "hfsm2")
        self.cpp_info.set_property("cmake_target_name", "hfsm2")
        self.cpp_info.components["hfsm2"].set_property("cmake_target_name", "hfsm2::hfsm2")
        self.cpp_info.components["hfsm2"].includedirs = ["include"]
        self.cpp_info.components["hfsm2"].libs = []