#!/usr/bin/env python3
"""Conan recipe — xsel 1.2.1 (X11 剪贴板命令行工具)

Build system: autotools (configure.ac + Makefile.am)
License: HPND-sell-variant
Homepage: https://github.com/kfish/xsel

OHOS adaptations:
  - GitHub tag archive 不含预生成 configure（autoreconf 产物不进版本库），
    build() 先 autoreconf 自举；真机缺 automake/aclocal/libtoolize（E178），
    经 tool_requires 用 build profile 解析（同 afuse/argp-standalone）。
  - configure.ac 用 PKG_CHECK_MODULES([X], [x11])：需要 pkg.m4（aclocal
    阶段）与 x11.pc（configure 阶段）。pkg.m4 动态定位 pkg-config 安装目录
    （aircrack-ng 同法）；x11.pc 来自 conan 依赖 libx11/6.4.0（ohpcd 已发布
    OHOS armv8 binary，kxl/libxscrnsaver 同法），经 PkgConfigDeps 生成到
    generators 目录，再由 build() 作用域注入 PKG_CONFIG_PATH。
  - E114: 生成的 configure 用 umask 077 建临时目录，HMDFS 下不可写 → 改 022。
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XselConan(ConanFile):
    name = "xsel"
    version = "1.2.1"
    description = "Command-line program for getting and setting the contents of the X selection"
    license = "HPND-sell-variant"
    homepage = "https://github.com/kfish/xsel"
    url = "https://github.com/kfish/xsel"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 依赖走 conan：libx11/6.4.0 在 ohpcd 已发布 OHOS armv8 binary
        # （kxl/libxscrnsaver 同法），PkgConfigDeps 生成 x11.pc 供 configure
        # 的 PKG_CHECK_MODULES([X], [x11]) 使用；不再依赖 cmd-pkgs 预编译目录
        # （真机实测该目录无 x11.pc，见 notes.md 问题 6）。
        self.requires("libx11/6.4.0", headers=True, libs=True)

    def build_requirements(self):
        # GitHub tag archive 不含预生成 configure（autoreconf 产物不进版本库），
        # 须 autoreconf 自举；真机缺 automake/aclocal/libtoolize（E178），
        # 经 tool_requires 用 build profile 解析（同 afuse/argp-standalone）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps 把 libx11/6.4.0 的 x11.pc（含其依赖 xorgproto/xtrans/
        # libxcb 的 .pc）生成到 generators 目录，供 configure 的
        # PKG_CHECK_MODULES([X], [x11]) 使用。
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # autoreconf 生成的 config.guess（2024-07-27）认不出 HarmonyOS
        # （uname -s 输出 "HarmonyOS"），configure 报 'cannot guess build
        # type'（真机预检 2026-08-14）；显式指定 triplet 绕过（同
        # a52dec/0.7.4、xcb-util-renderutil/0.3.10）。
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        # HMFS/HMDFS 不支持 getcwd：把进程 cwd 切到 build_folder（路径查找可用、
        # 仅 getcwd 不可用），并预置 PWD，让子进程 shell 的 pwd 内建在 getcwd
        # 失败时走逻辑路径 $PWD（同 aribb24/1.0.4）
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass
        os.environ["PWD"] = self.build_folder

        os.umask(0)
        apply_conandata_patches(self)
        self._prepare_aclocal_path()
        # GitHub tag archive 无 configure（autoreconf 产物不进版本库），先自举
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        self._patch_configure()
        autotools = Autotools(self)
        # 真机 conan 2.x 的 tc.environment()/PkgConfigDeps 注入 PKG_CONFIG_PATH
        # 实测不生效（pidgin 笔记同款坑），改为 build() 内作用域注入：
        # generators 目录（PkgConfigDeps 生成的 x11.pc 等）+ 各依赖包
        # lib/pkgconfig。try/finally 保证 build() 返回前恢复环境变量。
        _pc_paths = [self.generators_folder]
        for _dep in self.dependencies.values():
            _pc_paths.append(os.path.join(_dep.package_folder, "lib", "pkgconfig"))
        _pkg_config_path = ":".join(_pc_paths)
        _prior_pkg_config_path = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = _pkg_config_path
        self.output.info(f"PKG_CONFIG_PATH (scoped) = {_pkg_config_path}")
        try:
            autotools.configure()
            autotools.make(args=["-j1"])
        finally:
            if _prior_pkg_config_path:
                os.environ["PKG_CONFIG_PATH"] = _prior_pkg_config_path
            else:
                os.environ.pop("PKG_CONFIG_PATH", None)

    def _patch_configure(self):
        """autoreconf 后改写生成的 configure：
        - E114: config.status 用 umask 077 建临时目录，HMDFS 下不可写 → 改 022；
        - HMFS 下 getcwd 不可达致 configure 报 'working directory cannot be
          determined'：按 autoconf 版本改写 pwd 判定（同 aribb24/1.0.4）——
          2.70+ 的 `ac_pwd=`pwd`` 追加 `2>/dev/null || ac_pwd="$PWD"` 兜底；
          2.69 的 `if (pwd) >/dev/null 2>&1` 追加 `|| test -n "$PWD"`。
          cd "$ac_pwd" 与 ls -di . 走路径查找，不受 getcwd 影响。"""
        cfg = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cfg):
            return
        with open(cfg, "r", encoding="utf-8") as f:
            text = f.read()
        if "umask 077" in text:
            text = text.replace("umask 077", "umask 022")
        if 'ac_pwd=`pwd`' in text and 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"' not in text:
            text = text.replace('ac_pwd=`pwd`', 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"')
        text = re.sub(
            r'if \(pwd\) >/dev/null 2>&1( && test -d "`pwd`")?; then :; else',
            r'if (pwd) >/dev/null 2>&1\1 || test -n "$PWD"; then :; else',
            text,
        )
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(text)

    def _prepare_aclocal_path(self):
        """pkg.m4（PKG_CHECK_MODULES 宏）供 aclocal 使用：动态定位 pkg-config
        安装目录（aircrack-ng 同法），并兜底扫描 hnp 工具链 aclocal 目录（afuse 同法）。"""
        dirs = []
        pkg_config = shutil.which("pkg-config")
        if pkg_config:
            prefix = os.path.dirname(os.path.dirname(os.path.realpath(pkg_config)))
            cand = os.path.join(prefix, "share", "aclocal")
            if os.path.isfile(os.path.join(cand, "pkg.m4")):
                dirs.append(cand)
        for d in sorted(glob.glob("/data/service/hnp/*/*/share/aclocal")):
            if os.path.isfile(os.path.join(d, "pkg.m4")):
                dirs.append(d)
        if dirs:
            existing = os.environ.get("ACLOCAL_PATH", "")
            os.environ["ACLOCAL_PATH"] = ":".join(dirs + ([existing] if existing else []))

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 命令行工具：bin/xsel，无可链接库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
