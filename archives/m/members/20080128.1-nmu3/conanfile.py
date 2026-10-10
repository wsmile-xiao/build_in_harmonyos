#!/usr/bin/env python3
"""Conan recipe for members 20080128.1-nmu3 — list the members of a group.

members 是 groups(1) 的补集：groups 列出某用户所属的组，members 列出某个
组的成员（主组成员来自 getpwent 枚举 pw_gid，附属组成员来自 getgrnam 的
gr_mem）。单文件 C++ 程序（members.cc），只依赖 libc / libstdc++·libc++，
构建系统是裸 GNU Makefile（无 configure），上游无测试套件。

OHOS 适配点（详见同目录 notes.md）：

1. 无源码补丁：NDK clang++ / musl 下 members.cc 原样编译通过
   （getopt_long / getgrnam / getpwent 均为 musl 现成接口）。
2. 只在 make 命令行覆盖 CXX（上游 `CXX ?= g++`），编译器取自 Conan conf
   （R33，不裸用 ${CXX}）；CPPFLAGS 保持上游默认 `-g -Wno-deprecated`。
3. 不走 `make install`：上游 install 规则写死 `$(DESTDIR)/usr/bin/members`
   且要求目录预先存在，改在 package() 按 Conan 布局落 bin/members 与
   share/man/man1/members.1。
4. 上游 Makefile 无 strip 步骤，链接产物直接交付，不需要 E077 的重签。
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class MembersConan(ConanFile):
    name = "members"
    version = "20080128.1-nmu3"
    description = ("members lists the members of a group: the complement "
                   "of groups(1)")
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/members"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # 把 profile [buildenv]（PATH / LD_LIBRARY_PATH）带进 conanbuild：
        # PATH 决定 make 的解析，LD_LIBRARY_PATH 是 SDK lld 找 libxml2 的前提
        env = VirtualBuildEnv(self)
        env.generate()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)  # 本包无补丁，保持与仓库配方同构

        # R33：编译器取自 Conan conf，绝不裸用 shell 的 ${CXX}/${CXXFLAGS}
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        self.run(f"make -C {self.source_folder} CXX={cxx} -j1",
                 env="conanbuild")

    def package(self):
        copy(self, "members", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "members.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "copyright", src=os.path.join(self.source_folder, "debian"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # CLI 包：只暴露 bin/（R38 的 commands.json 在软件级目录）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
