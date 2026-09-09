#!/usr/bin/env python3
"""Conan recipe — c-list 3.1.0 (Meson header-only C11 intrusive list).

c-list 是 C-Util 项目的循环双向侵入式链表集合（ISO-C11），header-only：
上游仅安装 src/c-list.h 头文件与 pkg-config 描述，无库目标。上游自带
3 个纯 C 测试套件（meson test 注册，零外部依赖），在配方 build() 内
随 conan create 真实执行；交叉编译环境仅编译验证。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class CListConan(ConanFile):
    name = "c-list"
    version = "3.1.0"
    description = "Circular Intrusive Double Linked List Collection"
    license = "Apache-2.0 OR LGPL-2.1-or-later"
    homepage = "https://github.com/c-util/c-list"
    url = "https://github.com/c-util/c-list"
    topics = ("c", "linked-list", "intrusive", "header-only", "collection")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # 上游构建系统为 Meson（制品仓已发布，account-utils/1.4.0 同款先例）
        self.tool_requires("meson/1.11.0")

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only 库，所有 settings 组合产出相同的包内容
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # §6.2: CI worker 的 PATH 不含 llvm-ar/llvm-ranlib，Meson 在 project()
        # 阶段探测链接器会失败；从 profile compiler_executables 的编译器绝对
        # 路径推导同目录工具，写入 machine file 的 [binaries]
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") if compilers else None
        if cc:
            tool_dir = os.path.dirname(cc)
            tc.binaries["ar"] = os.path.join(tool_dir, "llvm-ar")
            tc.binaries["ranlib"] = os.path.join(tool_dir, "llvm-ranlib")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if not cross_building(self):
            # 上游测试套件：3 套件 11 个测试用例（纯 C assert，零外部依赖）
            meson.test()
        else:
            self.output.info("cross-building: upstream meson test skipped (compile-only)")

    def package(self):
        # 上游无 install 目标产物可自动化（仅 install_headers + pkgconfig），
        # 直接从源码树收纳唯一头文件（R26/R38：纯库，无 bin）
        copy(self, "c-list.h", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "c-list")
        self.cpp_info.set_property("cmake_target_name", "c-list::c-list")
        self.cpp_info.libs = []
