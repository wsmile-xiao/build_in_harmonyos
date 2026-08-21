#!/usr/bin/env python3
"""Conan recipe — itstool 2.0.7 (GNOME ITS tool — DocBook/XML translation)

itstool 提供 itstool 命令（Python 脚本，autotools 构建），依赖
libxml2（Python 模块——itstool 运行时 import libxml2）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ItstoolConan(ConanFile):
    name = "itstool"
    version = "2.0.7"
    description = "itstool — Translate documents with XML markup using PO files"
    license = "GPL-3.0-or-later"
    homepage = "https://itstool.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    # stubs/ 随 recipe 导出（libxml2.py——OHOS 无 python-libxml2，stub 让
    # itstool import 成功（--version 可用）；核心功能受限如实申报）
    exports_sources = "stubs/*"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("libxml2/2.15.3")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        build_dir = self.build_folder
        src_dir = self.source_folder
        # mktemp wrapper（config.status 的 mktemp -d 创建 0700 目录——HMDFS
        # 跨用户不可写——subs1.awk Permission denied——wrapper chmod 0755，
        # 同 dvdauthor 先例）
        wrapper = os.path.join(build_dir, "mktemp-wrap")
        with open(wrapper, "w") as f:
            # 绝对路径 mktemp（command mktemp 会递归解析到 wrapper 自身——
            # PATH 前缀 build_dir）——/bin/mktemp 或 /usr/bin/mktemp
            f.write('#!/bin/sh\n'
                    'out=$(/usr/bin/mktemp "$@" 2>/dev/null || '
                    '/bin/mktemp "$@")\n'
                    'chmod 0755 "$out" 2>/dev/null || true\n'
                    'echo "$out"\n')
        os.chmod(wrapper, 0o755)
        # configure + make（itstool.in Python 脚本 → itstool 可执行脚本）
        self.run(
            f"umask 000 && cd {build_dir} && "
            # PYTHON 用 PATH 里的 python3（/usr/local/bin/python3 系统路径
            # 不存在——实际在 /storage/Users/currentUser/usr/local/bin/python3）
            f"PATH={build_dir}:$PATH "
            f"PYTHON=$(command -v python3) "
            f"{src_dir}/configure --prefix=/usr/local",
            env="conanbuild",
        )
        self.run(
            f"umask 000 && cd {build_dir} && make -j1",
            env="conanbuild",
        )

    def package(self):
        # DESTDIR install（itstool 脚本 + data/ ITS 规则文件）
        self.run(
            f"DESTDIR={self.package_folder} make -C "
            f"{self.build_folder} install",
            env="conanbuild",
        )
        # stub libxml2.py 复制到 itstool 同目录（usr/local/bin/——itstool 脚本
        # 的 sys.path[0]——import libxml2 成功——--version 可用）
        stub_py = os.path.join(self.source_folder, "stubs", "libxml2.py")
        if os.path.exists(stub_py):
            copy(self, "libxml2.py", src=os.path.dirname(stub_py),
                 dst=os.path.join(self.package_folder, "usr", "local", "bin"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["usr/local/bin"]
