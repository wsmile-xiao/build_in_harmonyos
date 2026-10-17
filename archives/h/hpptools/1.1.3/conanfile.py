#!/usr/bin/env python3
"""Conan recipe — hpptools 1.1.3（C++11 header-only 工具库集合）.

hpptools 是纯 header-only 库（include/*.hpp），无编译产物：
alg/logsum/logsumset/logdiff/logger/pfor/tpool/strict_fstream/zstr 等。
zstr.hpp 在公开头文件里 include <zlib.h>（gz 流包装），因此配方声明
zlib 为唯一公开链接需求；消费者经 CMakeDeps/生成器自动获得 zlib 头路径。

R32: 无 settings.os 分支需要——OHOS 适配版 conan 自动映射
os=OHOS → 交叉工具链。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class HpptoolsConan(ConanFile):
    name = "hpptools"
    version = "1.1.3"
    description = "A collection of C++11 header-only utility libraries (logger, zstr, alg, logsum, pfor, tpool, strict_fstream)"
    license = "MIT"
    homepage = "https://github.com/mateidavid/hpptools"
    url = "https://github.com/mateidavid/hpptools"  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zstr.hpp 公开头 include <zlib.h>，zlib 为唯一公开依赖
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：无编译；若存在补丁先应用
        apply_conandata_patches(self)

    def package(self):
        # 安装全部公开头文件到 include/
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        # 保留许可证
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # header-only：无可链接库文件
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "hpptools")
        self.cpp_info.set_property("cmake_target_name", "hpptools::hpptools")
