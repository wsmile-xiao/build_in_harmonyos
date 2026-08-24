#!/usr/bin/env python3
"""Conan recipe for skymaker 3.10.5 (simulated sky image generator —
AstrOmatic suite, autotools).

Dependencies:
  - fftw3f (single-precision FFTW — skymaker uses fftwf_ API)
  - pthread (disabled via --enable-threads=no — OHOS lacks
    pthread_cancel declaration)

sdist includes pre-generated configure + Makefile.in.
"""
import os
import re
import glob as _glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SkymakerConan(ConanFile):
    name = "skymaker"
    version = "3.10.5"
    description = "Simulated sky image generator (AstrOmatic suite)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.astromatic.net/software/skymaker"
    url = "https://github.com/astromatic/skymaker"
    exports_sources = "conandata.yml", "patches/*"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        # skymaker 用单精度 FFTW API（fftwf_）——fftw3f/3.3.9 已发布
        self.requires("fftw3f/3.3.9")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["skymaker"],
            strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        fftw = self.dependencies["fftw3f"]
        tc.configure_args.extend([
            # 注意：不加 --build（scamp 同款 config.guess patch 已内联
            # 识别 OHOS——CI 上显式 --build 导致 C compiler works 检查
            # 失败实测（psfex/weightwatcher/skymaker 三库同报））
            "--with-fftw-libdir=%s" % os.path.join(
                fftw.package_folder, "lib"),
            "--with-fftw-incdir=%s" % os.path.join(
                fftw.package_folder, "include"),
            # OHOS pthread.h 未声明 pthread_cancel（同 swarp 实测）——
            # 禁用多线程（单线程模式完全可用）
            "--enable-threads=no",
        ])
        # 编译期头文件/链接路径注入（--with-fftw-incdir 仅 configure
        # 检查阶段生效——make 编译仍需 -I 和 -L——同 sextractor 实测）
        tc.extra_cflags.append(
            "-I%s" % os.path.join(fftw.package_folder, "include"))
        tc.extra_ldflags.append(
            "-L%s" % os.path.join(fftw.package_folder, "lib"))
        tc.generate()

    def _patch_ohos_autotools(self):
        """config.guess/config.sub 内联补 OHOS 识别（同 scamp 先例）。"""
        aux = os.path.join(self.source_folder, "autoconf")
        cg = os.path.join(aux, "config.guess")
        cs = os.path.join(aux, "config.sub")
        if os.path.isfile(cg):
            text = open(cg, encoding="utf-8", errors="ignore").read()
            changed = False
            if "HarmonyOS" not in text:
                # skymaker 的 config.guess 是旧版（2007-05-17——各分支
                # 自行 echo+exit 输出，无统一 echo $GUESS 逻辑）——
                # 必须用旧版格式插入（新版 GUESS= 变量格式实测
                # 匹配后不输出——unable to guess system type）
                block = (
                    "    *:HarmonyOS:*:*)\n"
                    "\techo ${UNAME_MACHINE}-unknown-linux-ohos\n"
                    "\texit ;;\n\n")
                new = re.sub(r"(^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)",
                             block + r"\1", text, flags=re.M)
                changed = new != text
                text = new
            if changed:
                open(cg, "w", encoding="utf-8").write(text)
                self.output.info("已修补 config.guess: 加入 HarmonyOS 识别")
        if os.path.isfile(cs):
            text = open(cs, encoding="utf-8", errors="ignore").read()
            changed = False
            if "linux-ohos" not in text:
                # skymaker 的 config.sub 是旧版（2007-04-29——无
                # android-linux 分支，scamp 的新版 patch 模式不匹配
                # 实测）——按旧版格式加 ohos os 支持：
                # 1) maybe_os 列表加 linux-ohos*
                # 2) os 合法性列表加 -linux-ohos*
                # 3) -linux* 分支前加 -linux-ohos 特判（避免被
                #    sed s|linux|linux-gnu| 错误改写）
                text = text.replace(
                    "nto-qnx* | linux-gnu* | linux-dietlibc | "
                    "linux-newlib* | linux-uclibc*",
                    "nto-qnx* | linux-gnu* | linux-ohos* | "
                    "linux-dietlibc | linux-newlib* | linux-uclibc*",
                    1)
                text = text.replace(
                    "-linux-gnu* | -linux-newlib* | -linux-uclibc*",
                    "-linux-gnu* | -linux-ohos* | -linux-newlib* | "
                    "-linux-uclibc*", 1)
                old = ("\t-linux*)\n"
                       "\t\tos=`echo $os | sed -e 's|linux|linux-gnu|'`")
                new = ("\t-linux-ohos)\n"
                       "\t\tos=-linux-ohos\n"
                       "\t\t;;\n"
                       "\t-linux*)\n"
                       "\t\tos=`echo $os | sed -e 's|linux|linux-gnu|'`")
                if old in text:
                    text = text.replace(old, new, 1)
                changed = True
            if changed:
                open(cs, "w", encoding="utf-8").write(text)
                self.output.info("已修补 config.sub: 加入 ohos os 支持")

    def build(self):
        os.umask(0)
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # sdist 含预生成 configure——config.guess 不含 OHOS——内联补丁
        self._patch_ohos_autotools()
        # OHOS: configure 内 umask 077 建临时目录失败——改 000
        for _cfg in _glob.glob(
                os.path.join(self.source_folder, "**", "configure"),
                recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 000"))
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # sky 是命令行工具，无库文件
