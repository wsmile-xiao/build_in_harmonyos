#!/usr/bin/env python3
"""Conan recipe for inheritenv — GNU Emacs Lisp package.

inheritenv makes temporary buffers inherit buffer-local environment variables
(process-environment / exec-path). Pure Elisp data package: no C/C++ sources,
nothing to compile or link. Installed to lib/site-lisp per the merged ace-link
precedent; byte-compilation is left to Emacs at load time.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class InheritenvConan(ConanFile):
    name = "inheritenv"
    version = "0.2"
    description = ("GNU Emacs package: make temp buffers inherit buffer-local "
                   "environment variables")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/purcell/inheritenv"
    url = ""  # CI fills this

    # 纯 Elisp 数据包，无 shared 选项（ace-link 先例范式）
    # settings 四项齐全（L0p 门禁要求 OHOS profile 全部四项；ace-link 老写法
    # "os", "arch" 已不再通过 L0p）
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 纯 Elisp 数据包无编译步骤。构建期防漂移：发行文件在位、行数合理
        # （上游 0.2 实测：inheritenv.el 87 行、inheritenv-tests.el 38 行）。
        for fname, expect in (("inheritenv.el", (70, 120)),
                              ("inheritenv-tests.el", (25, 60))):
            path = os.path.join(self.source_folder, fname)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(
                    f"inheritenv 0.2 inventory drift: missing {fname}"
                )
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = sum(1 for _ in fh)
            if not (expect[0] <= lines <= expect[1]):
                raise ConanInvalidConfiguration(
                    f"inheritenv 0.2 inventory drift: {fname} has {lines} lines"
                )
        if not os.path.isfile(os.path.join(self.source_folder, "README.md")):
            raise ConanInvalidConfiguration(
                "inheritenv 0.2 inventory drift: missing README.md"
            )

    def package(self):
        # 与 ace-link 同款布局：.el 源文件装到 lib/site-lisp，
        # Emacs 经 load-path 直接加载（R1：不跑上游 Makefile 的
        # compile/package-lint/test 目标，均需 Emacs 运行时与 MELPA 网络）。
        copy(self, "*.el", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib", "site-lisp"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib", "site-lisp"))

    def package_id(self):
        # 纯数据包无编译产物：清空 package_id，避免 compiler/build_type
        # 造成无意义的包分裂（header-only 模板范式）
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["lib/site-lisp"]
        self.cpp_info.libdirs = []
