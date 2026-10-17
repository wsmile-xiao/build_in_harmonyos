#!/usr/bin/env python3
"""Conan recipe — potool 0.19（纯 C 裸 Makefile，无 configure/CMake）。

要点（详见 notes.md 问题表 1–7）：
  - R9  -j1；R33 CC/CFLAGS 走调用行（CI worker 上 ${CC}/${CFLAGS} 环境变量为空）
  - manifest build.system=makefile 显式覆盖（G0 探测链与模板选择按其走）
  - Makefile 用 $(shell pkg-config …) 取 glib → 需 PkgConfigDeps 生成的 .pc + PKG_CONFIG_PATH
  - OHOS 无 locale 命令 → build() 内生成最小环境 shim（不改上游源码）
  - 上游测试 make check 在 build() 内真跑（N=10）
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

# 最小 locale shim：OHOS/musl 全机无 `locale` 命令（W0 关④五路 MISS）。
# 上游 scripts/poedit 只用 `locale charmap`，UTF-8 locale 的 glibc 真实输出即 `UTF-8`
# （返回 locale 名 `C.UTF-8` 会被 iconv 判 conversion unsupported —— 实测）。
_LOCALE_SHIM = """#!/bin/sh
case "$1" in
  charmap) printf 'UTF-8\\n' ;;
  *) printf '%s\\n' "${LC_ALL:-C.UTF-8}" ;;
esac
"""


class PotoolConan(ConanFile):
    name = "potool"
    version = "0.19"
    description = "Program for manipulating gettext po files (filter, stats and editing helpers)"
    license = "GPL-2.0-or-later"
    homepage = "https://marcin.owsiany.pl/potool-page"
    url = "https://github.com/porridge/potool"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # PkgConfigDeps 生成 glib-2.0.pc（Makefile 走 $(shell pkg-config …)）；
    # VirtualBuildEnv 提供 conanbuild（tool_requires 的 flex/bison/pkgconf/gettext 进 PATH）
    generators = "PkgConfigDeps", "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 运行期唯一链接依赖（Makefile: GLIB_LIB/GLIB_INCLUDE 走 pkg-config）
        self.requires("glib/2.88.3")

    def build_requirements(self):
        # flex/bison 生成 lex.po.c / po.tab.c；pkgconf 提供 Makefile 的 $(shell pkg-config …)；
        # gettext 提供 msgfmt（scripts/poupdate 用）
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")
        self.tool_requires("pkgconf/3.0.6")
        self.tool_requires("gettext/0.22.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33：整体取 dict 再索引（`:c` 子键写法在 Conan 2.29 直接抛异常）
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp.get("c") or "clang"

        # ① OHOS 无 `locale` → 最小环境 shim（环境层，不改上游源码）
        shim_dir = os.path.join(self.build_folder, "ohos-bin")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "locale")
        with open(shim, "w", encoding="utf-8") as fh:
            fh.write(_LOCALE_SHIM)
        os.chmod(shim, 0o755)

        # ② 构建环境：PKG_CONFIG_PATH 指向 PkgConfigDeps 生成的 .pc；
        #    TMPDIR/HOME 都钉在 conan build 目录（设备 /tmp 只读；上游测试不写真实 HOME）
        env = Environment()
        env.define_path("PKG_CONFIG_PATH", self.generators_folder)
        env.define_path("TMPDIR", self.build_folder)
        env.define_path("HOME", self.build_folder)
        env.define("LC_ALL", "C.UTF-8")
        env.prepend_path("PATH", shim_dir)
        env.vars(self).save_script("potool_build")
        # conanbuild = tool_requires(flex/bison/pkgconf/gettext) 入 PATH；
        # conanrun   = LD_LIBRARY_PATH 指向 glib（make check 直跑 ../potool 必需）
        run_env = ["conanbuild", "conanrun", "potool_build"]

        # R9: -j1；CFLAGS 按工作区口径钉（-Werror 已由 0001-Makefile.patch 移除）
        cflags = "-O3 -pipe -DNDEBUG -g -Wall"
        self.run(
            f"make CC={cc} CFLAGS='{cflags}' -j1",
            cwd=self.source_folder,
            env=run_env,
        )

        # 上游测试：make check（N=10，见 notes.md「上游测试」表）
        self.run("make check", cwd=self.source_folder, env=run_env)

    def package(self):
        # 设备 PATH 不含 /system/bin（CI worker 含），install 二进制按 which → 绝对路径回退
        install = shutil.which("install") or "/system/bin/install"
        self.run(
            f"make install DESTDIR='{self.package_folder}' INSTALL='{install}'",
            cwd=self.source_folder,
        )

    def package_info(self):
        # 可执行包：无 lib/include（bindirs 默认 bin/，PF8 要求配套 commands.json）
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
