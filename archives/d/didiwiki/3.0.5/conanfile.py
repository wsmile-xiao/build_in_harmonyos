#!/usr/bin/env python3
"""Conan recipe — didiwiki 3.0.5 (CiWiki).

CiWiki is a small personal wiki engine with a built-in HTTP server, written
in C with zero external library dependencies (libc only). Upstream 3.0.x is
released as "ciwiki" on SourceForge; the executable is `ciwiki`. Debian keeps
the historical source package name "didiwiki" for the same tarball.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DidiwikiConan(ConanFile):
    name = "didiwiki"
    version = "3.0.5"
    description = "CiWiki (didiwiki) — a small personal wiki engine with an integrated HTTP server"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/ciwiki/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # 上游 tarball 成员名带 "./" 前缀（GNU tar 打包），conan 的 strip_root 对这类
        # 归档只会剥离 "./" 而不会把唯一根目录上移，导致源码落在 ciwiki-3.0.5/ 子目录。
        # 先解包到干净的临时目录，再把唯一根目录的内容上移到 source_folder 根。
        tmp_dir = os.path.join(self.source_folder, "_extract")
        get(self, **self.conan_data["sources"], destination=tmp_dir)
        src_root = tmp_dir
        entries = os.listdir(tmp_dir)
        if len(entries) == 1 and os.path.isdir(os.path.join(tmp_dir, entries[0])):
            src_root = os.path.join(tmp_dir, entries[0])
        for entry in os.listdir(src_root):
            shutil.move(os.path.join(src_root, entry), os.path.join(self.source_folder, entry))
        shutil.rmtree(tmp_dir)
        # tarball 携带作者的构建残留（in-tree configure 产物）。conan 走 VPATH 构建
        # （build 目录里执行 configure），残留的 config.status 会触发
        # "source directory already configured; run make distclean" 错误。
        # 这些文件均由 configure 重新生成，直接清理。
        residues = [
            "config.status", "config.log", "config.h", "stamp-h1",
            "Makefile",
            os.path.join("src", "Makefile"),
            os.path.join("scripts", "Makefile"),
            os.path.join("docs", "Makefile"),
        ]
        for residue in residues:
            path = os.path.join(self.source_folder, residue)
            if os.path.isfile(path):
                os.remove(path)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
