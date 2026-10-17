#!/usr/bin/env python3
"""Conan recipe — fifo_map 1.0.1（Header-only，变体 A）.

上游 nlohmann/fifo_map：FIFO 顺序保持的关联容器，header-only（src/fifo_map.hpp），
仅依赖 STL，无编译阶段。配方采用 header-only 族（v12.21 conanfile-headeronly 模板）：
source() 下载官方 tag 压缩包，package() 仅拷贝头文件到 include/。
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout

import os


class FifoMapConan(ConanFile):
    name = "fifo_map"
    version = "1.0.1"
    description = "fifo_map — FIFO-ordered associative container for C++ (header-only)"
    license = "MIT"
    homepage = "https://github.com/nlohmann/fifo_map"
    url = ""  # CI fills this

    package_type = "header-library"

    # 无编译产物 → settings 仅保留结构一致性；package_id 清空见下
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # 无编译阶段：header-only 无 configure/make；build() 仅应用补丁（空 patches 为 no-op），
    # 不伪造编译日志（R34）
    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # 变体 A: header-only 库 — 拷贝头文件（上游位于 src/fifo_map.hpp，装到 include/ 根
        # 以匹配 README 与消费者习惯的 `#include <fifo_map.hpp>`）与许可证
        copy(self, "fifo_map.hpp", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        # 变体 A: 标准头文件信息
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "fifo_map")
        self.cpp_info.set_property("cmake_target_name", "fifo_map::fifo_map")
        self.cpp_info.components["fifo_map"].set_property(
            "cmake_target_name", "fifo_map::fifo_map")