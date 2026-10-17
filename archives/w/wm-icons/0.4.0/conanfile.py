#!/usr/bin/env python3
"""Conan recipe for wm-icons 0.4.0 — 窗口管理器图标集（纯资源包）。

上游: https://tracker.debian.org/pkg/wm-icons （Debian 源码包即上游分发形态）
源码分发: https://deb.debian.org/debian/pool/main/w/wm-icons/wm-icons_0.4.0.orig.tar.gz
（本配方走清华 TUNA 镜像同一份文件，sha256 与 .dsc 的 Checksums-Sha256 一致）

`wm-icons` 的设计核心是一份**标准化图标名清单** `icons/names.lst`（84 个名字，
如 `amusement`、`calculator`、`cd-player`、`window-close`），31 个图标集各自用
PNG 或 XPM 实现这份清单的一（部分）子集，再由各窗口管理器的 rc 把语义名指向
具体图标。本包把整棵图标树作为资源交付：

    share/wm-icons/<31 个图标集目录>/    828 个 PNG + 1210 个 XPM + 每集一份 _symlinks.lst
    share/wm-icons/names.lst             84 个标准图标名
    share/doc/wm-icons/                  FAQ / README.* / icons.lst
    licenses/COPYING

**纯资源包，无编译步骤**：上游的 autotools 只用于安装（`icons/Makefile.am` 的
`install-data-local` 把每个图标集 `tar` 进 `$(icondir)`），不编译任何代码。
本配方按同样语义直接拷贝，不调用 configure/make —— 因此也不需要 OHOS 工具链。

有意不安装的部分（见 notes.md 与 PR 说明）：`bin/`（`#!/bin/sh` + 需要运行
`wm-icons-config` 生成符号链接，OpenHarmony 无 `/bin`）、`etc/`（fvwm/scwm 的 rc
模板，面向的窗口管理器在鸿蒙上不存在）、`devel/`、`rpm/`。

License: GPL-2.0-or-later
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches, get
from conan.tools.layout import basic_layout


class WmIconsConan(ConanFile):
    name = "wm-icons"
    version = "0.4.0"
    description = ("Window Manager Icons — 31 themed icon sets implementing a "
                   "standardized 84-name icon list (PNG + XPM)")
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/wm-icons"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯资源包：无编译、无 settings，产物与架构无关。
    package_type = "unknown"

    no_copy_source = True

    _data_subdir = os.path.join("share", "wm-icons")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 没有编译器参与（上游 autotools 只做安装），这里只做本体自检：
        # 图标树与标准名清单必须都在，否则"装出来的图标集"没有可用语义名。
        icons_dir = os.path.join(self.source_folder, "icons")
        names_lst = os.path.join(icons_dir, "names.lst")
        if not os.path.isdir(icons_dir):
            raise ConanException("upstream icons/ directory missing")
        if not os.path.isfile(names_lst):
            raise ConanException("upstream icons/names.lst missing")

        sets = [d for d in os.listdir(icons_dir)
                if os.path.isdir(os.path.join(icons_dir, d))]
        if len(sets) < 30:
            raise ConanException(
                f"expected >=30 icon sets upstream, found {len(sets)}")

        with open(names_lst, encoding="utf-8", errors="replace") as handle:
            names = [line.strip() for line in handle
                     if line.strip() and not line.startswith("#")]
        if len(names) < 80:
            raise ConanException(
                f"expected the standardized 84-name list, found {len(names)}")
        self.output.info(f"wm-icons: {len(sets)} icon sets, {len(names)} standard names")

    def package(self):
        data_dir = os.path.join(self.package_folder, self._data_subdir)

        icons_dir = os.path.join(self.source_folder, "icons")
        for entry in sorted(os.listdir(icons_dir)):
            src = os.path.join(icons_dir, entry)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=os.path.join(data_dir, entry))
        copy(self, "names.lst", src=icons_dir, dst=data_dir)

        copy(self, "FAQ", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "doc", "wm-icons"))
        copy(self, "README*", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "doc", "wm-icons"))
        copy(self, "icons.lst", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "doc", "wm-icons"))

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 资源包：没有库、没有可执行文件、没有头文件（E255 的 forbid_1）。
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        self.cpp_info.resdirs = [os.path.join("share", "wm-icons")]

        data_dir = os.path.join(self.package_folder, self._data_subdir)
        self.buildenv_info.define("WM_ICONS_DIR", data_dir)
        self.runenv_info.define("WM_ICONS_DIR", data_dir)
        self.output.info(f"WM_ICONS_DIR={data_dir}")
