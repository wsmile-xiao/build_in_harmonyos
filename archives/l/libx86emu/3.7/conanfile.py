#!/usr/bin/env python3
"""Conan recipe — libx86emu 3.7 (plain Makefile project, no configure).

适配要点（详见 notes.md）：
- 上游 3.7 tarball 不含 VERSION 文件（由 git2log 生成），构建前需写入 VERSION。
- 上游仅提供 shared 构建（Makefile 无静态库规则），故 default shared=True。
- git2log 为上游预编译二进制（x86_64 ELF），本平台不可执行；构建前移除以
  避免 Makefile 顶层变量求值时的 stderr 噪声，保证 VERSION 解析确定性。
- 本机/CI 无 coreutils `install` 命令，package() 手工落位（cp/ln），不依赖
  Makefile 的 install 目标。
- CC 显式传 clang（R33：不依赖未定义的 shell 环境变量）。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Libx86EmuConan(ConanFile):
    name = "libx86emu"
    version = "3.7"
    description = "Small C library to emulate x86 instructions (upstream: wfeldt/libx86emu)"
    license = "MIT"
    homepage = "https://github.com/wfeldt/libx86emu"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 1) tarball 缺失 VERSION：上游由 git2log 生成，这里显式写入
        self.run("echo 3.7 > VERSION", cwd=self.source_folder)
        # 2) 移开异架构的预编译 git2log，避免 Makefile 顶层 $(shell) 求值噪声
        if os.path.exists(os.path.join(self.source_folder, "git2log")):
            self.run("mv git2log git2log.upstream", cwd=self.source_folder)
        # 3) 纯 Makefile 工程：无 configure，直接构建 shared 目标
        self.run("make shared CC=clang -j1", cwd=self.source_folder)

    def package(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        copy(self, "libx86emu.so.3.7", self.source_folder, lib_dir)
        self.run("ln -s libx86emu.so.3.7 libx86emu.so.3", cwd=lib_dir)
        self.run("ln -s libx86emu.so.3 libx86emu.so", cwd=lib_dir)
        copy(self, "x86emu.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", self.source_folder, self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["x86emu"]
        self.cpp_info.set_property("cmake_file_name", "libx86emu")
        self.cpp_info.set_property("cmake_target_name", "libx86emu::libx86emu")
