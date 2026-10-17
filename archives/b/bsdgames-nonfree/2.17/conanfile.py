#!/usr/bin/env python3
"""Conan recipe — bsdgames-nonfree 2.17 (custom interactive configure).

bsd-games-non-free 2.17 仅包含 rogue 游戏（NetBSD roguelike）。
构建系统为自定义交互式 configure 脚本（非标准 autotools），
通过 bsd_games_cfg_* 环境变量预设配置（非交互模式）。
依赖 ncurses/6.4 静态库。
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class BsdgamesnonfreeConan(ConanFile):
    name = "bsdgames-nonfree"
    version = "2.17"
    description = "bsd-games-non-free 2.17 — rogue (NetBSD roguelike game)"
    license = "BSD-3-Clause"
    homepage = "https://www.ibiblio.org/pub/Linux/games/"
    url = "https://www.ibiblio.org/pub/Linux/games/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"bsdgames-nonfree supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ncurses_flags(self):
        """从 ncurses 依赖提取 include/lib 标志（ncurses 包无 .pc 文件，需显式传递）。"""
        nc = self.dependencies["ncurses"]
        pkg = nc.package_folder
        inc_dirs = getattr(nc.cpp_info, "includedirs", None) or []
        lib_dirs = getattr(nc.cpp_info, "libdirs", None) or []
        lib_names = getattr(nc.cpp_info, "libs", None) or []
        nc_inc = " ".join(f"-I{os.path.join(pkg, d)}" for d in inc_dirs)
        nc_lib = " ".join(f"-L{os.path.join(pkg, d)}" for d in lib_dirs)
        nc_libs = " ".join(f"-l{l}" for l in lib_names)
        return nc_inc, f"{nc_lib} {nc_libs}".strip()

    def _configure_env(self, install_prefix):
        """构造 configure 非交互所需的 bsd_games_cfg_* 环境变量。"""
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc = executables.get("c", "clang")
        nc_inc, nc_lib = self._ncurses_flags()
        return {
            "bsd_games_cfg_non_interactive": "y",
            "bsd_games_cfg_cc": cc,
            "bsd_games_cfg_optimize_flags": "-O2",
            "bsd_games_cfg_ncurses_includes": nc_inc,
            "bsd_games_cfg_ncurses_lib": nc_lib,
            "bsd_games_cfg_do_chown": "n",
            "bsd_games_cfg_gzip_manpages": "n",
            "bsd_games_cfg_use_libcrypto": "n",
            "bsd_games_cfg_install_prefix": install_prefix,
        }

    def build(self):
        apply_conandata_patches(self)
        # R49: staging 使用 build_folder 私有目录（不注入共享前缀）
        staging = os.path.join(self.build_folder, "staging")
        env = Environment()
        for key, value in self._configure_env(staging).items():
            env.define(key, value)
        env.vars(self).save_script("conanbuildenv")

        self.run("./configure", cwd=self.source_folder, env="conanbuildenv")
        self.run("make -j1", cwd=self.source_folder, env="conanbuildenv")
        self.run("make install", cwd=self.source_folder, env="conanbuildenv")

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        # 安装布局: staging/usr/games/rogue → bin/,
        #           staging/usr/share/man → share/man,
        #           staging/usr/share/doc → share/doc
        copy(self, "*", src=os.path.join(staging, "usr/games"), dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*", src=os.path.join(staging, "usr/share/man"), dst=os.path.join(self.package_folder, "share/man"))
        copy(self, "*", src=os.path.join(staging, "usr/share/doc"), dst=os.path.join(self.package_folder, "share/doc"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
