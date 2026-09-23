#!/usr/bin/env python3
"""Conan recipe — nsnake 3.0.1.1 (ncurses snake game).

nsnake 是终端 ncurses 贪吃蛇游戏，上游用纯 Makefile（非 autotools），
ncurses 由 Conan 依赖提供。

3.0.1.1 是 3.0.1 的**适配修复版**（R37 版本号后缀递增），实质变化在
`package()` / `package_info()` 与 `build()` 的日期传参：
① 上游 `make install` 除可执行文件外还会安装 31 个关卡、man6 手册、两种尺寸的
图标、xpm 与 desktop 入口，而 3.0.1 只打包了 `bin/nsnake`，这些资产在制品中丢失；
② 上游 `Makefile:42 DATE = $(shell date "+%b%Y")` 使二进制内嵌构建月份、产物不可
复现，本版本向 make 传 `DATE='Jul2014'` 固定（GNU Make 命令行赋值优先）。
编译/链接参数、依赖、补丁与 `source()` 逻辑均沿用 3.0.1。OHOS 上没有 `install(1)`（也没有
E108 方案要求的 `ginstall`），所以这里用 Conan 的 copy()/save() 复现同一套 FHS
数据布局，而不是调 `make install`。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.layout import basic_layout

# 上游 levels/*.nsnake 的数量，作为打包回归基线（v3.0.1 实测 31 个）
_LEVEL_COUNT = 31
# 上游 `Makefile:42 DATE = $(shell date "+%b%Y")` 会把构建月份编进二进制
# （`-DDATE=...`，见 `nsnake --version`）并写进手册，两者都不可复现。这里把日期
# 固定为上游 v3.0.x 发布月的 `%b%Y` 形态（July 2014 -> `Jul2014`），同时供
# `build()` 的 make 命令行与 man6 占位符替换共用，使 L5 产物基线可复现。
_BUILD_DATE = "Jul2014"


class NsnakeConan(ConanFile):
    name = "nsnake"
    version = "3.0.1.1"
    description = "nsnake - classic snake game on the terminal using ncurses"
    license = "GPL-3.0"
    homepage = "https://github.com/alexdantas/nSnake"
    url = "https://github.com/alexdantas/nSnake"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        # R39: 官方 URL 下载 + sha256 校验（CI 自动添加镜像 fallback，配方内不手写镜像）
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = ce.get("c", "clang")
        cxx = ce.get("cpp", "clang++")

        src = self.source_folder

        # Get ncurses dependency info from the Conan dependency
        dep = self.dependencies["ncurses"]
        cpp_info = dep.cpp_info
        ncurses_inc = ":".join(cpp_info.includedirs) if cpp_info.includedirs else os.path.join(dep.package_folder, "include")
        ncurses_lib = ":".join(cpp_info.libdirs) if cpp_info.libdirs else os.path.join(dep.package_folder, "lib")
        ncurses_libs = " ".join(f"-l{lib}" for lib in cpp_info.libs)

        cxxflags = f"-O2 -Wall -Wextra -I{ncurses_inc}"
        # Override LDFLAGS entirely (the Makefile's default LDFLAGS has
        # -lncurses, but the wide-character build produces libncursesw.a).
        ldflags = f"-L{ncurses_lib} {ncurses_libs}"

        # Build with the Makefile.
        # `clean` 在首次构建时必然因无产物而失败（源码目录每次新建），属预期，忽略。
        self.run(
            f"make -C {src} clean", ignore_errors=True
        )
        # GNU Make 的命令行赋值优先于 Makefile 内的 `DATE = $(shell date ...)`，
        # 传 DATE= 才能让 -DDATE 与 --version 输出可复现。
        self.run(
            f"make -C {src} -j1 V=1 CC={cc} CXX={cxx} "
            f"CXXFLAGS='{cxxflags}' "
            f"CFLAGS_PLATFORM='-I{ncurses_inc}' "
            f"LDFLAGS='{ldflags}' "
            f"DATE='{_BUILD_DATE}' "
            f"PREFIX=/usr"
        )

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # 可执行文件（与 3.0.1 一致）
        copy(self, "nsnake",
             src=os.path.join(src, "bin"),
             dst=os.path.join(pkg, "bin"))

        # 上游 $(LEVELDIR) = $(DATAROOTDIR)/games/nsnake/levels
        copy(self, "*.nsnake",
             src=os.path.join(src, "levels"),
             dst=os.path.join(pkg, "share", "games", "nsnake", "levels"))

        # 上游图标 / pixmaps / desktop 入口（install -pm644 会重命名，这里等价实现；
        # conan 2.29 的 copy() 无 dst_filename 参数，故用 copy + os.replace）
        misc = os.path.join(src, "misc")
        self._install_as("nsnake16.png", misc,
                         os.path.join(pkg, "share", "icons", "hicolor", "16x16", "apps"),
                         "nsnake.png")
        self._install_as("nsnake32.png", misc,
                         os.path.join(pkg, "share", "icons", "hicolor", "32x32", "apps"),
                         "nsnake.png")
        self._install_as("nsnake32.xpm", misc,
                         os.path.join(pkg, "share", "pixmaps"), "nsnake.xpm")
        self._install_as("nsnake.desktop", misc,
                         os.path.join(pkg, "share", "applications"), "nsnake.desktop")

        self._package_manpage(src, pkg)
        self._verify_packaging(pkg)

    def _install_as(self, pattern, src, dst_dir, filename):
        copy(self, pattern, src=src, dst=dst_dir)
        moved = os.path.join(dst_dir, pattern)
        target = os.path.join(dst_dir, filename)
        if os.path.isfile(moved) and moved != target:
            os.replace(moved, target)

    def _package_manpage(self, src, pkg):
        """复现上游 install 的 sed 替换：s|DATE|..|g; s|VERSION|..|g。"""
        template = os.path.join(src, "doc", "man", "nsnake.6")
        text = load(self, template)
        upstream_ver = self._upstream_makefile_version(src)
        rendered = text.replace("VERSION", upstream_ver).replace("DATE", _BUILD_DATE)
        if re.search(r"\b(VERSION|DATE)\b", rendered):
            raise ConanException(
                f"man 模板占位符未替换干净: {os.path.basename(template)}")
        manpath = os.path.join(pkg, "share", "man", "man6", "nsnake.6")
        save(self, manpath, rendered)

    def _upstream_makefile_version(self, src):
        """上游 Makefile 的 VERSION（v3.0.1 仍写 3.0.0），用于手册与 --version 一致性。"""
        text = load(self, os.path.join(src, "Makefile"))
        m = re.search(r"^VERSION\s*=\s*(\S+)", text, re.M)
        if not m:
            raise ConanException("无法从上游 Makefile 解析 VERSION，手册版本占位符不可信")
        return m.group(1)

    def _verify_packaging(self, pkg):
        """打包回归基线：缺任一上游资产即失败，防止再次退化成只发一个二进制。"""
        expected_files = [
            "bin/nsnake",
            "share/man/man6/nsnake.6",
            "share/pixmaps/nsnake.xpm",
            "share/applications/nsnake.desktop",
            "share/icons/hicolor/16x16/apps/nsnake.png",
            "share/icons/hicolor/32x32/apps/nsnake.png",
        ]
        missing = [f for f in expected_files
                   if not os.path.isfile(os.path.join(pkg, f))]
        if missing:
            raise ConanException(f"打包缺文件: {missing}")
        empty = [f for f in expected_files
                 if os.path.getsize(os.path.join(pkg, f)) == 0]
        if empty:
            raise ConanException(f"打包空文件: {empty}")
        level_dir = os.path.join(pkg, "share", "games", "nsnake", "levels")
        levels = [f for f in os.listdir(level_dir) if f.endswith(".nsnake")] \
            if os.path.isdir(level_dir) else []
        if len(levels) != _LEVEL_COUNT:
            raise ConanException(
                f"关卡数不符: 期望 {_LEVEL_COUNT}，实际 {len(levels)}")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
