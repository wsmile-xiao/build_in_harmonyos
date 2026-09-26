#!/usr/bin/env python3
"""Conan recipe for json.h 3.15 (header-only, C/C++ single-header JSON parser).

Patch 0001: test/test_shared.h 顶部 `-Wunsafe-buffer-usage` 诊断忽略仅对
Clang >= 16 存在，Clang 15（OHOS 工具链）下被 -Werror 提升为
`unknown warning group [-Werror,-Wunknown-warning-option]` 编译错误；
用 __has_warning 守卫（与同文件 -Wglobal-constructors 等既有模式一致）。
该文件属上游测试源，不参与打包，但补丁随配方保存以保证上游测试可在
OHOS 工具链上复现编译运行。
"""
import os
from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class JsonHConan(ConanFile):
    name = "json.h"
    version = "3.15"
    description = "A simple single header solution to parsing JSON in C and C++"
    license = "Unlicense"
    homepage = "https://github.com/sheredom/json.h"
    url = "https://github.com/sheredom/json.h"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 无编译阶段（header-only），仅应用补丁后由 package() 拷贝头文件。
        # 不得伪造编译日志（R34）。
        apply_conandata_patches(self)

    def package(self):
        copy(self, "json.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # 无编译产物，不依赖 os/compiler 二进制差异
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []  # header-only：无链接库（test_package 真实编译链接验证）
        self.cpp_info.set_property("cmake_file_name", "json.h")
        self.cpp_info.set_property("cmake_target_name", "json.h")
