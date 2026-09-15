#!/usr/bin/env python3
"""Conan recipe — CLEX File Manager 4.6.patch8 (curses 终端文件管理器).

上游 http://www.clex.sk（源码经 archive.ubuntu.com pristine orig 获取，Debian dsc 互证）。
发行包自带 autoconf 2.69 生成的 configure（无 AC_CANONICAL_HOST、无 config.guess），
无外部构建工具依赖；唯一依赖 ncursesw（AC_SEARCH_LIBS addwstr）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain


class ClexConan(ConanFile):
    name = "clex"
    version = "4.6.patch8"
    description = "CLEX File Manager: a terminal file manager with a curses UI"
    license = "GPL-2.0-only"
    homepage = "http://www.clex.sk"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 宽字符 curses 界面：configure 以 AC_SEARCH_LIBS(addwstr, [ncursesw ...])
        # 硬性探测，缺失即报错（alpine/2.26 同款依赖与接线先例）
        self.requires("ncurses/6.5")

    def layout(self):
        # src/Makefile 的 help.inc 规则用裸相对路径（无 $(srcdir)），
        # out-of-source 构建报 "convert.sed: No such file or directory"；
        # 改 in-source 构建（compface/1.5.2 同款修复）
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = os.path.join(".", "conan")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # AC_SEARCH_LIBS(addwstr) 的链接探测与 curses 头文件都需要指向 ncurses 包
        # （AutotoolsToolchain 无 extra_cppflags 属性，用 extra_cflags，CI #21036 同款）
        ncurses = self.dependencies["ncurses"]
        tc.extra_ldflags.append(f"-L{os.path.join(ncurses.package_folder, 'lib')}")
        tc.extra_cflags.append(f"-I{os.path.join(ncurses.package_folder, 'include')}")
        tc.generate()
        # ncurses 包的 pkgconfig 目录（若 configure 走 pkg-config 分支）
        env = Environment()
        env.append_path(
            "PKG_CONFIG_PATH",
            os.path.join(ncurses.package_folder, "lib", "pkgconfig"),
        )
        env.vars(self, scope="build").save_script("clex_pkgconfig")

    def build(self):
        apply_conandata_patches(self)

        # E011：autoconf 2.69 生成的 configure 用 `umask 077 && mktemp -d` 建临时
        # 目录，HMDFS 上得到 0700+setgid 组合导致 config.status 写 subs*.awk
        # 报 Permission denied（探索构建实证）。设备侧与 CI worker 均为 HMDFS
        # 类环境，直接放宽临时目录 umask（E011 方法 2，保留真实临时目录创建）。
        cfg_path = os.path.join(self.source_folder, "configure")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = f.read()
        if "umask 077" in cfg:
            cfg = cfg.replace("umask 077", "umask 022")
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write(cfg)
            os.chmod(cfg_path, 0o755)
            self.output.info("  [ok] E011: configure umask 077 -> 022")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 工具类包：交付 bin/clex、bin/kbd-test、bin/cfg-clex 与 man 页
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
