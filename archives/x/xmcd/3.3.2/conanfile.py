#!/usr/bin/env python3
"""Conan recipe for xmcd (Motif CD player / CD ripper suite).

Source: https://pkg.freebsd.org/ports-distfiles (upstream tikan.org distfile mirror)
Build system: Makefile.std —— OHOS 无 imake/xmkmf 工具链，使用上游自带的
              Makefile.std 直接构建（README 给出的官方备选路径，与 xli 同路径）。

平台适配要点（详见 notes.md）：
  1. OHOS musl libc 无 <termio.h> → 补丁 0001 允许从构建命令行选择 USE_TERMIOS
  2. OHOS musl libc 不提供 pthread_cancel(3)/pthread_setcancelstate(3) →
     补丁 0002 引入 HAVE_PTHREAD_CANCEL 特性宏：=0 时自中止路径收敛为
     pthread_exit()，跨线程取消点（心跳超时路径）降级为记录 + 空操作
  3. musl 未定义 HZ（仅 SCSI Generic 超时路径使用）→ 编译期 -DHZ=100
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, chdir, copy, export_conandata_patches, get
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class XmcdConan(ConanFile):
    name = "xmcd"
    version = "3.3.2"
    description = ("xmcd - Motif CD player/ripper suite (xmcd GUI, cda command-line "
                   "player/ripper, gobrowser CDDB browser)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.tikan.org/ti/xmcd/"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Makefile.std / make.inc 的真实依赖面：XLIBS = -lXm -lXt -lXext -lX11（+ SM/ICE 传递）
        self.requires("motif/2.3.8")
        self.requires("libxt/1.3.1")
        self.requires("libxext/6.4.0.1")
        # motif/libxt pin libx11/1.8.13，libxext 自带 pin libx11/6.4.0：
        # 与 libXmu/1.3.1 相同的化解方式——force 到 1.8.13
        self.requires("libx11/1.8.13", force=True)
        # cda 的 CURSESLIB = -lcurses（包内提供 ncursesw 静态库）
        self.requires("ncurses/6.6")

    # R32: settings.os 判断必须兼容 OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # R33: 编译器/基础标志由 Conan 工具链注入，不裸用 shell 环境变量
        tc = GnuToolchain(self)
        tc.generate()

    def _compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get("c") or str(self.settings.compiler)

    def _dependency_flags(self):
        """展开依赖的 -I/-L/-l（Makefile.std 不经 autotools，需显式传参）。"""
        includes, libdirs, libs = [], [], []
        for dep in self.dependencies.values():
            info = dep.cpp_info.aggregated_components()
            includes.extend(info.includedirs or [])
            libdirs.extend(info.libdirs or [])
            for name in info.libs or []:
                if name not in libs:
                    libs.append(name)
        inc_flags = " ".join(f"-I{p}" for p in dict.fromkeys(includes))
        ld_flags = " ".join(f"-L{p}" for p in dict.fromkeys(libdirs))
        lib_flags = " ".join(f"-l{n}" for n in libs)
        return inc_flags, ld_flags, lib_flags

    def build(self):
        apply_conandata_patches(self)
        inc_flags, ld_flags, lib_flags = self._dependency_flags()
        # 参数最少化：仅保留平台必需项（-DUSE_TERMIOS / -DHZ=100 / -DHAVE_PTHREAD_CANCEL=0）
        cflags = (
            f"-O2 -fPIC -I{self.source_folder} {inc_flags} "
            "-DUSE_TERMIOS -DHZ=100 -DHAVE_PTHREAD_CANCEL=0 "
            "-DHAS_ICONV_H -DHAS_NCURSES_H -D_REENTRANT"
        )
        deps_ld = f"{ld_flags} {lib_flags}"
        with chdir(self, self.source_folder):
            # Makefile.std 的 Makefiles 目标把各级 Makefile.std 复制为 Makefile
            self.run("make -f Makefile.std Makefiles")
            # R9: 固定 -j1（HMDFS/任务机限制）
            self.run(
                "make -j1 "
                f"CC='{self._compiler()}' "
                f"CFLAGS='{cflags}' "
                "DEFINES='' ARCH='' MISC='' ENCODERS='' "
                f"XLIBS='{deps_ld}' "
                f"CURSESLIB='{deps_ld}' "
                f"CDDBLIB='-L{self.source_folder}/cddb_d -lcddb' "
                "SOCKETLIB='' ENCLIBS='' AUDIOLIB='' MATHLIB='-lm' PTHREADLIB=''"
            )

    def package(self):
        copy(self, "xmcd", os.path.join(self.source_folder, "xmcd_d"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "cda", os.path.join(self.source_folder, "cda_d"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "gobrowser", os.path.join(self.source_folder, "util_d"),
             os.path.join(self.package_folder, "bin"))
        # 手册页（xmcd_d/xmcd.man、cda_d/cda.man）
        copy(self, "*.man", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"))
        # Motif app-defaults（GUI 外观/资源）
        copy(self, "XMcd.ad", os.path.join(self.source_folder, "xmcd_d"),
             os.path.join(self.package_folder, "share", "X11", "app-defaults"))
        copy(self, "COPYING", os.path.join(self.source_folder, "docs_d"),
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # CLI 工具包：仅暴露 bin/（commands.json 见软件级目录）
        self.cpp_info.bindirs = ["bin"]
