#!/usr/bin/env python3
"""Conan recipe — alien 8.95.9 (Perl package format converter).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL + make).
alien converts between rpm/dpkg/slp/tgz package formats. Pure-Perl program
(no C/XS) — the build only generates the `alien` executable script.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy


class AlienConan(ConanFile):
    name = "alien"
    version = "8.95.9"
    description = "Convert or install an alien binary package (rpm/dpkg/slp/tgz)"
    license = "GPL-2.0-or-later"
    homepage = "http://kitenet.net/~joey/code/alien/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # 纯 Perl 程序——仅用 Perl 核心模块（Alien/Package/*.pm 无外部 CPAN 依赖）；
        # perl 运行时由 OHOS 系统提供（/data/service/hnp/bin/perl——CI PATH 内置）
        pass

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # alien 是纯 Perl 程序——跳过 Makefile.PL/make 的 EXE_FILES 拷贝
        # （make 的 blib/script/alien 目标问题 + alien 与源码目录冲突——
        # 实测 sh: can't create alien: Is a directory）——直接按 Makefile.PL
        # 的 alien 规则生成可执行脚本 alien_gen（移除 use lib 调试行 +
        # VERSION_AUTOREPLACE → our $Version="8.95.9";）
        self.run("perl -pe '$_=\"\" if /^use lib/; "
                 "s/our \\$Version=.unknown.;.*$/our \\$Version=\"8.95.9\";/' "
                 "alien.pl > alien_gen", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "alien_gen", src=src, dst=bin_dir)
        # conan 的 copy 不支持 rename 参数（实测 TypeError）——拷贝后改名 alien
        os.rename(os.path.join(bin_dir, "alien_gen"), os.path.join(bin_dir, "alien"))
        # Alien/Package/*.pm（alien.pl 运行的包格式模块——use lib 路径）
        copy(self, "*.pm", src=os.path.join(src, "Alien"),
             dst=os.path.join(self.package_folder, "lib", "Alien"))
        copy(self, "*.pm", src=os.path.join(src, "Alien", "Package"),
             dst=os.path.join(self.package_folder, "lib", "Alien", "Package"))
        for doc in ("GPL", "README", "INSTALL", "TODO"):
            copy(self, doc, src=src,
                 dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
        # alien.pl 的 use lib（Alien/Package/*.pm——PERL5LIB 指向包 lib）
        self.env_info.PERL5LIB.append(os.path.join(self.package_folder, "lib"))
