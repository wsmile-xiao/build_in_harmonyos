#!/usr/bin/env python3
"""Conan recipe for debconf — Debian 包配置管理框架（纯 Perl，无编译）。

debconf 是纯 Perl 实现（Debconf/*.pm 模块 + debconf-* 系列 CLI 脚本），
上游 Makefile 仅有 doc/po 文档构建，核心模块无需编译。本配方：
- source() 获取官方 Debian 源包（work/ 为顶层目录，strip_root）
- package() 拷贝 Debconf/**/*.pm 到 <pkg>/lib/perl5/，可执行脚本到 <pkg>/bin/
- 依赖核验：Debconf 模块仅 use Perl 核心模块（IO::File、File::Temp、POSIX、
  Text::Wrap、Text::Tabs、File::Spec、Exporter 等）+ 内部 Debconf::* 模块，
  无外部 CPAN 依赖。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import download, copy
from conan.tools.layout import basic_layout


class DebconfConan(ConanFile):
    name = "debconf"
    version = "1.5.77"
    description = "Debian package configuration management system (pure Perl)"
    license = "BSD-2-Clause"
    homepage = "https://salsa.debian.org/pkg-debconf/debconf"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        # 沙箱下 get() 解压 work/ 根目录 tar 会抛 IsADirectoryError（dpkg 同款
        # 限制）——改用 download() + 手动 tar 解压，--strip-components=1 去掉 work/
        # 另：目标文件系统大小写不敏感，tar 内 work/Debconf/（目录）与
        # work/debconf（文件）同名冲突——用 --transform 把文件改名 debconf.tool
        tarball = "debconf_1.5.77.tar.xz"
        src = self.conan_data["sources"]
        download(self, src["url"], filename=tarball, sha256=src["sha256"])
        # xz 解压到当前目录（strip 顶层 work/ + 规避大小写冲突）
        self.run(
            f"tar -xJf {tarball} --strip-components=1 --no-same-owner "
            "--transform='s|^work/debconf$|work/debconf.tool|'",
            cwd=self.source_folder)
        os.remove(os.path.join(self.source_folder, tarball))

    def build(self):
        # 纯 Perl 库——无需编译（上游 Makefile 仅构建 doc/po）
        pass

    def package(self):
        src = self.source_folder
        # Perl 模块：Debconf/**/*.pm → lib/perl5/
        lib_dest = os.path.join(self.package_folder, "lib", "perl5")
        for root, _dirs, files in os.walk(os.path.join(src, "Debconf")):
            for f in files:
                if f.endswith(".pm"):
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, src)
                    copy(self, rel, src, lib_dest)
        # 可执行脚本 → bin/
        bin_dest = os.path.join(self.package_folder, "bin")
        for f in os.listdir(src):
            if f.startswith("debconf") or f in ("confmodule", "confmodule.sh",
                                                "check_db.pl"):
                fp = os.path.join(src, f)
                if os.path.isfile(fp) and os.access(fp, os.X_OK):
                    copy(self, f, src, bin_dest)
        # source() 中 --transform 把 debconf 文件改名 debconf.tool（规避大小写
        # 冲突），这里还原为 bin/debconf
        if os.path.isfile(os.path.join(bin_dest, "debconf.tool")):
            os.rename(os.path.join(bin_dest, "debconf.tool"),
                      os.path.join(bin_dest, "debconf"))
        # 配置文件与 Python 辅助模块
        if os.path.isfile(os.path.join(src, "debconf.conf")):
            copy(self, "debconf.conf", src,
                 os.path.join(self.package_folder, "etc", "debconf"))
        if os.path.isfile(os.path.join(src, "debconf.py")):
            copy(self, "debconf.py", src,
                 os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Perl 应用——无可链接库
        self.cpp_info.libs = []
