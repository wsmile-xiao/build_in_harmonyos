#!/usr/bin/env python3
"""Conan recipe — brynet 1.12.2 (C++11 header-only TCP network library).

brynet 是 IronsDu 维护的跨平台高性能 TCP 网络库，官方 README 明确
"Header Only ... using C++ 11"：全部实现位于 include/brynet/ 头文件，
上游 CMakeLists.txt 只 install 头文件目录，无库编译产物。
因此本配方采用 header-only 打包（package_type=header-library）。
可选 OpenSSL（未安装时自动禁用，BYNET_USE_OPENSSL 不定义，非必需依赖）。
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BrynetConan(ConanFile):
    name = "brynet"
    version = "1.12.2"
    description = "Header only cross platform high performance TCP network library using C++ 11"
    license = "MIT"
    homepage = "https://github.com/IronsDu/brynet"
    url = ""  # CI fills this
    topics = ("network", "tcp", "header-only", "cpp11", "event-loop")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # 无编译阶段：header-only，build() 留空（R34：不得伪造编译日志）

    def build(self):
        pass

    def package(self):
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()  # header-only 无 ABI 依赖，单一 package_id

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "brynet")
        self.cpp_info.set_property("cmake_target_name", "brynet::brynet")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []