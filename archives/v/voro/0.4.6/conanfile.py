#!/usr/bin/env python3
"""Conan recipe — voro++ 0.4.6 (3D cell-based Voronoi tessellation library).

voro++ 是一个三维 Voronoi 泰森多边形库，采用 cell-based 计算方式。
核心类：voronoicell（单个 Voronoi 单元）、container（粒子容器）。

构建系统：GNU Make（config.mk + src/Makefile）
特点：纯 C++ 库，无外部依赖

注意：voro++ v0.4.6 不包含 CMakeLists.txt，使用 GNU Make 构建。
源码顶层 config.mk 定义编译器(CXX=g++)和编译选项(CFLAGS)，
src/Makefile 编译 .cc -> .o 并用 ar 打包为 libvoro++.a。
"""
import os
from conan import ConanFile
from conan.tools.files import get, replace_in_file, copy
from conan.tools.env import VirtualBuildEnv


class VoroConan(ConanFile):
    name = "voro"
    version = "0.4.6"
    description = "3D cell-based Voronoi tessellation library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/chr1shr/voro"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: 通过 VirtualBuildEnv 生成标准构建环境
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        # R33: 从 Conan conf 获取编译器路径，禁止依赖 shell 环境变量
        # tools.build:compiler_executables 是 dict 类型：{'c': '...', 'cpp': '...'}
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cxx = comp.get("cpp", "clang++") if comp else "clang++"
        # 根据 build_type 动态生成 CFLAGS（Release/RelWithDebInfo/Debug）
        config_mk = os.path.join(self.source_folder, "config.mk")
        build_type = str(self.settings.build_type)
        if build_type == "Release":
            opt_flags = "-O3"
        elif build_type == "RelWithDebInfo":
            opt_flags = "-O2 -g"
        elif build_type == "Debug":
            opt_flags = "-O0 -g"
        else:
            opt_flags = "-O3"
        new_cflags = f"-Wall -ansi -pedantic {opt_flags}"
        # 添加 -fPIC（位置无关代码，供静态库嵌入共享库时使用）
        # Windows 上 fPIC 选项已被 config_options 删除，get_safe 默认 False
        if self.options.get_safe("fPIC", False):
            new_cflags += " -fPIC"
        replace_in_file(
            self, config_mk,
            "CFLAGS=-Wall -ansi -pedantic -O3",
            f"CFLAGS={new_cflags}",
        )
        # 仅构建静态库（跳过命令行工具和示例）
        # src/Makefile 的 libvoro++.a target 编译 .cc -> .o 并用 ar 打包
        # make 命令行 CXX=... 覆盖 config.mk 中的 CXX=g++（避免 shell 变量展开问题）
        src_dir = os.path.join(self.source_folder, "src")
        self.run(f'make -C "{src_dir}" libvoro++.a CXX="{cxx}"', env="conanbuild")

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        # 复制静态库 libvoro++.a -> lib/
        copy(
            self, "libvoro++.a",
            src=src_dir,
            dst=os.path.join(self.package_folder, "lib"),
        )
        # 复制头文件 *.hh -> include/voro++/
        # voro++ 的头文件互相 #include "*.hh"，需放在同一目录
        copy(
            self, "*.hh",
            src=src_dir,
            dst=os.path.join(self.package_folder, "include/voro++"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "VORO")
        self.cpp_info.set_property("cmake_target_name", "VORO::voro++")
        self.cpp_info.libs = ["voro++"]
        # 头文件安装在 include/voro++/，消费者可用 #include "voro++.hh"
        self.cpp_info.includedirs = ["include/voro++"]
