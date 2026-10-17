#!/usr/bin/env python3
"""Conan recipe — kakoune 2025.06.03 (Makefile).

Kakoune is a lightweight code editor.
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout
import os

class KakouneConan(ConanFile):
    name = "kakoune"
    version = "2025.06.03"
    license = "UNLICENSE"
    author = "mawww"
    url = "https://github.com/mawww/kakoune"
    description = "Kakoune is a code editor"
    package_type = "application"
    exports_sources = "patches/*"
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 从 Conan settings 获取编译器，不硬编码
        cxx = {"clang": "clang++", "gcc": "g++", "apple-clang": "clang++"}.get(
            str(self.settings.compiler), "c++")
        # HMDFS 不允许 symlink：上游 Makefile:110 ln -sf kak$(tag) $@ 报 Permission denied.
        # 改 ln -sf → cp -f 硬拷代替 symlink，绕 HMDFS symlink 禁止。
        makefile = os.path.join(self.source_folder, "Makefile")
        if os.path.exists(makefile):
            with open(makefile) as f:
                mk_content = f.read()
            mk_content = mk_content.replace("\tln -sf kak$(tag) $@", "\tcp -f src/kak$(tag) $@")
            with open(makefile, "w") as f:
                f.write(mk_content)
        ret = self.run(f"make -j2 CXX={cxx}", cwd=self.source_folder, env="conanbuild")
        if ret != 0:
            raise ConanException(f"make failed with exit code {ret}")
        # make install 也要显式传 CXX，否则上游默认用 c++ 报 'c++: inaccessible or not found'
        ret = self.run(f"make install CXX={cxx} DESTDIR=./install PREFIX=/usr/local", cwd=self.source_folder, env="conanbuild")
        if ret != 0:
            raise ConanException(f"make install failed with exit code {ret}")
        # 上游 test/run 用 mkfifo 创建 FIFO 通信管道，HMDFS 不允许 mkfifo 报
        # 'Operation not permitted' → 无法跑上游测试。kakoune 是 application，
        # 消费者级测试由 test_package 提供，跳过上游 test/run。

    def package(self):
        copy(self, "kak", src=os.path.join(self.source_folder, "install", "usr", "local", "bin"), dst=os.path.join(self.package_folder, "bin"))
        # 递归复制 rc/ 子目录（* 不能跨目录匹配，需用 keep_path 或逐个复制）
        rc_src = os.path.join(self.source_folder, "rc")
        rc_dst = os.path.join(self.package_folder, "share", "kak")
        for root, dirs, files in os.walk(rc_src):
            for f in files:
                full_src = os.path.join(root, f)
                rel_path = os.path.relpath(full_src, rc_src)
                full_dst = os.path.join(rc_dst, rel_path)
                os.makedirs(os.path.dirname(full_dst), exist_ok=True)
                copy(self, f, src=os.path.dirname(full_src), dst=os.path.dirname(full_dst))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]