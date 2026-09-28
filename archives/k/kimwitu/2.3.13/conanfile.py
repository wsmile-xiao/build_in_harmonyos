#!/usr/bin/env python3
"""Conan recipe for kimwitu (Kimwitu++) 2.3.13 — C++ compiler construction toolkit.

Autotools 构建（自举：boot 目标用 Gen.boot/ 预生成解析器源重建 kc++）。
鸿蒙适配点（均为实测）：
  1) config.status 的 tmp 创建（umask 077 && mktemp -d "./confXXXXXX"）被安全框架
     拦截（脚本子进程写新建临时目录 → Permission denied），patch 0001 改为
     TMPDIR 绝对路径 + 去掉 umask。
  2) 动态链接的 kc++（依赖 /system/lib64/libc++_shared.so）执行报
     "Operation not permitted"（execve EPERM），静态链接版本正常；
     patch 0002 让 boot 目标链接 kc++ 时强制 -static（动态版实测无法运行）。
  3) boot 目标的 strip 原地改写文件被拦（strip: unable to copy file），
     patch 0002 同时禁用该 strip。
产物：bin/kc++（kimwitu++ 编译器）+ man 页。无库依赖（无需 openssl 等）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class KimwituConan(ConanFile):
    name = "kimwitu"
    version = "2.3.13"
    description = "Kimwitu++ - a compiler construction toolkit for generating C++ code from tree specifications"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/kimwitu-pp/"
    url = "https://www.nongnu.org/kimwitu-pp/"
    topics = ("compiler", "code-generation", "parser", "toolkit")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # 用 conan 标准 get() 下载：CI mirror fallback 会把 conandata.yml 的
        # url 改写成 URL 列表（['mirror', 'official']），原手动 curl 拼接列表
        # 报 "bad range specification"（CI #61718）；get() 原生支持 URL 列表/
        # mirror 回退，并内置 sha256 校验与 strip_root 目录提升。
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # tarball 无 config.guess/config.sub，AutotoolsToolchain 显式传
        # --build/--host（跳过 config.guess 探测），configure 由此可运行
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # TMPDIR 兜底（patch 0001 后 config.status 的临时目录走 $TMPDIR，
        # 必须指向已存在的可写目录——安全框架拦"新目录里写文件"）
        tmpdir = os.environ.get("TMPDIR", "")
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-e", "-j1"])

    def package(self):
        # Makefile 的 install 规则不创建目录（/system/bin/install -c 不 mkdir），
        # 预建 bin/ 与 man 目录（首次 install 前 package_folder 为空）
        for rel_dir in ("bin", "share/man/man1"):
            os.makedirs(os.path.join(self.package_folder, rel_dir), exist_ok=True)
        autotools = Autotools(self)
        # make install 触发 boot：patch 0002 已让 boot 链接静态 kc++ 并
        # 禁用 strip（strip 原地写被拦），产物为可执行的静态 kc++
        autotools.install()
        # man 页从源码树复制（build 目录无 man/，install 规则已删 man 行）
        man_src = os.path.join(self.source_folder, "man", "man1", "kc++.1")
        man_dst = os.path.join(self.package_folder, "share", "man", "man1", "kc++.1")
        shutil.copy(man_src, man_dst)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "kimwitu")
        self.cpp_info.set_property("cmake_target_name", "kimwitu::kimwitu")
