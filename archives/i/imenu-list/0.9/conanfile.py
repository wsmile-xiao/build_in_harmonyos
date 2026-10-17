#!/usr/bin/env python3
"""Conan recipe for imenu-list 0.9 (single-file Emacs Lisp package).

imenu-list shows the imenu entries of the current Emacs buffer in a separate
buffer ("*Ilist*") as a navigable, collapsible outline with live updates.
It ships as a single Emacs Lisp file (imenu-list.el, Package-Requires:
cl-lib 0.5); there are no C/C++ sources and nothing to link. Following the
merged web-mode 17.3.20 precedent, the build is byte-compilation driven by
the published emacs/29.1 Conan package, and the package installs the
.el/.elc pair under share/emacs/site-lisp/imenu-list-<version>/.

License: GPL-3.0-or-later (upstream LICENSE file carries the GNU GPL v3
text; the .el header has the matching notice).
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class ImenuListConan(ConanFile):
    name = "imenu-list"
    version = "0.9"
    description = ("Emacs package that shows the current buffer's imenu "
                   "entries in a separate navigable buffer")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/bmag/imenu-list"
    url = "https://github.com/bmag/imenu-list"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # 上游 v0.9 实测：imenu-list.el 686 行（构建期防漂移区间）
    _elisp = "imenu-list.el"
    _elisp_lines = (620, 750)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("emacs/29.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"imenu-list supports Linux and OHOS, got {self.settings.os}"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "imenu-list is an architecture-independent Elisp package"
            )

    def package_id(self):
        # 纯 Elisp 包无编译产物分裂维度：清空 package_id
        # （web-mode / inheritenv 同款 header-only 模板范式）
        self.info.clear()

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _emacs(self):
        dependency = self.dependencies["emacs"]
        emacs = os.path.join(dependency.package_folder, "bin", "emacs")
        if not os.path.isfile(emacs):
            raise ConanInvalidConfiguration(
                f"Emacs executable is missing: {emacs}"
            )
        return shlex.quote(emacs)

    def build(self):
        apply_conandata_patches(self)
        # 上游发行包为单文件 elisp（无构建系统、无测试套件）：构建期防漂移
        # 校验清单与行数区间（上游 v0.9 实测 686 行），随后字节编译。
        path = os.path.join(self.source_folder, self._elisp)
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                f"imenu-list 0.9 inventory drift: missing {self._elisp}"
            )
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = sum(1 for _ in fh)
        if not (self._elisp_lines[0] <= lines <= self._elisp_lines[1]):
            raise ConanInvalidConfiguration(
                f"imenu-list 0.9 inventory drift: "
                f"{self._elisp} has {lines} lines"
            )
        # 字节编译（web-mode 先例：经已发布的 emacs/29.1 驱动）
        self.run(
            f"{self._emacs()} -Q --batch "
            f"-f batch-byte-compile {shlex.quote(path)}",
            env="conanbuild",
        )
        compiled = os.path.join(self.source_folder, "imenu-list.elc")
        if not os.path.isfile(compiled) or os.path.getsize(compiled) == 0:
            raise ConanException("imenu-list.elc was not produced")
        self.output.success("imenu-list.el byte-compiled with GNU Emacs 29.1 "
                            "(no errors; upstream 0.9 ships no test suite)")

    def package(self):
        lisp_dir = os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"imenu-list-{self.version}",
        )
        copy(self, "imenu-list.el", self.source_folder, lisp_dir)
        copy(self, "imenu-list.elc", self.source_folder, lisp_dir)
        copy(
            self,
            "README.md",
            self.source_folder,
            os.path.join(self.package_folder, "share", "doc", "imenu-list"),
        )
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        lisp_dir = os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"imenu-list-{self.version}",
        )
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.buildenv_info.define_path("IMENU_LIST_LISPDIR", lisp_dir)
        self.runenv_info.define_path("IMENU_LIST_LISPDIR", lisp_dir)
        self.buildenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
        self.runenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
