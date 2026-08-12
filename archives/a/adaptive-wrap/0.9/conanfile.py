#!/usr/bin/env python3
"""Conan recipe for adaptive-wrap 0.9 — Emacs Lisp 自适应换行包。

adaptive-wrap 是 GNU ELPA 的纯 Emacs Lisp 包（GPL-3.0-or-later），
提供 `adaptive-wrap-prefix-mode` minor mode：动态设置 wrap-prefix，
使长行段落按缩进自适应换行，且不修改 buffer 文本。

纯 elisp 无 C/C++ 编译：byte-compile 需要 Emacs 运行时（构建期
不可用，同 emacspeak 先例），.el 文件可直接被 Emacs 加载。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class AdaptiveWrapConan(ConanFile):
    name = "adaptive-wrap"
    version = "0.9"
    description = "Smart line-wrapping with wrap-prefix for Emacs"
    license = "GPL-3.0-or-later"
    homepage = "https://elpa.gnu.org/packages/adaptive-wrap.html"
    url = ""

    # 纯 elisp 包，无二进制产物；安装 .el 文件供 Emacs 加载
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 无编译：纯 Emacs Lisp 包。Byte compilation 需要 Emacs 运行时，
        # 构建期不可用；.el 文件可被 Emacs 直接加载（同 emacspeak 先例）。

    def package(self):
        # 安装 .el 文件到 share/emacs/site-lisp/，供 EMACSLOADPATH 加载
        site_lisp = os.path.join(self.package_folder, "share", "emacs", "site-lisp")
        copy(self, "*.el", src=self.source_folder, dst=site_lisp)
        if os.path.exists(os.path.join(self.source_folder, "news")):
            copy(self, "news", src=self.source_folder, dst=site_lisp)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = [os.path.join("share", "emacs", "site-lisp")]
