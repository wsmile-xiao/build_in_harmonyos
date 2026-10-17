#!/usr/bin/env python3
"""Conan recipe for cream 0.43 (Cream for Vim).

cream 是纯 Vim script 的数据/脚本型发行（无 C/C++ 代码、无编译），
按"拷贝安装"路线打包：不运行上游 INSTALL.sh（含 bashism，且依赖设备
PATH 中的 vim/perl 探测 $VIMRUNTIME 并写 /tmp，OHOS 设备不可直接执行），
在 package() 中用 conan.tools.files.copy 按上游安装布局写入
<prefix>/share/vim/cream/。
"""

import os

from conan import ConanFile
from conan.tools.files import copy, get


class CreamConan(ConanFile):
    name = "cream"
    version = "0.43"
    package_type = "application"

    description = "Cream (for Vim): a Vim script configuration layer that makes Vim easier to use for beginners"
    license = "GPL-3.0-or-later"
    homepage = "https://cream.sourceforge.net"
    url = "https://sourceforge.net/projects/cream"
    topics = ("vim", "editor", "vim-script", "configuration", "data")

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 无编译步骤：仅做源码完整性自检（tarball 完整性已由 conandata.yml
        # 的 SHA256 保证，这里校验关键运行时文件在位）
        src = self.source_folder
        for rel in ("creamrc", "cream.vim", "docs/COPYING.txt"):
            path = os.path.join(src, *rel.split("/"))
            if not os.path.isfile(path):
                raise Exception(f"source archive incomplete: missing {rel}")

    def package(self):
        src = self.source_folder
        dst = self.package_folder
        cream_dir = os.path.join(dst, "share", "vim", "cream")

        # 主配置 + 顶层 Vim 运行时脚本（与上游 INSTALL.sh 拷贝集一致，权限 0644）
        copy(self, "creamrc", src, cream_dir)
        copy(self, "*.vim", src, cream_dir)

        # 运行时子目录（上游 mkdir -p 的 7 个目录；lang 的安装行被上游脚本
        # 注释禁用，此处保留完整多语言菜单数据，均为惰性数据文件）
        for sub in ("addons", "bitmaps", "docs", "docs-html", "filetypes", "help", "lang"):
            copy(self, "*", os.path.join(src, sub), os.path.join(cream_dir, sub))

        # 桌面集成文件（上游安装到 PREFIX/share）
        copy(self, "cream.desktop", src, os.path.join(dst, "share", "applications"))
        copy(self, "cream.svg", src, os.path.join(dst, "share", "icons"))
        copy(self, "cream.png", src, os.path.join(dst, "share", "icons"))

        # 不打包宿主安装器与启动器（INSTALL.sh/INSTALL.bat/cream/cream.bat/
        # cream.ico）：launcher 依赖设备 PATH 中的 vim，交由运行环境集成，
        # 详见 notes.md

    def package_info(self):
        # 纯数据包：不提供头文件/库/可执行文件；运行宿主为 vim（仓内
        # archives/v/vim 为旧式归档、无 conan 配方，不作 conan requires）
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
