#!/usr/bin/env python3
"""Conan recipe — httpserver-h 0.0-git9029347a82 (header-only C HTTP server library).

上游: https://github.com/jeremycw/httpserver.h — 单头文件 C 库。
用法: 在唯一一个 C/C++ 文件中 `#define HTTPSERVER_IMPL` 后 include <httpserver.h>。
OHOS 平台使用 epoll 事件后端，消费者需在 include 前定义 EPOLL（见 test_package/test.c）。
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
import os


class HttpserverHConan(ConanFile):
    name = "httpserver-h"
    version = "0.0-git9029347a82"
    description = "A single header C library for building non-blocking event driven HTTP servers"
    license = "MIT"
    homepage = "https://github.com/jeremycw/httpserver.h"
    url = "https://github.com/jeremycw/httpserver.h"

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
        apply_conandata_patches(self)

    # 无编译阶段：header-only 库不产生编译日志（R34 禁止伪造编译），
    # build() 留空以满足 G1 配方完整性门禁
    def build(self):
        pass

    def package(self):
        # dst 必须为绝对路径：相对路径会被解析到 build 目录而非 package 目录
        copy(self, "httpserver.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()          # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "httpserver-h")
        self.cpp_info.set_property("cmake_target_name", "httpserver-h::httpserver-h")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []