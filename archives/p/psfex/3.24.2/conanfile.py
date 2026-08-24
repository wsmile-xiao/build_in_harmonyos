#!/usr/bin/env python3
"""Conan recipe for psfex 3.24.2 (PSF model builder — AstrOmatic suite,
autotools).

Dependencies:
  - fftw3f/3.3.9 (single-precision FFTW)
  - openblas/0.3.34 (BLAS/LAPACK)
  - plplot (optional plotting — disabled by default)
  - pthread (disabled via --enable-threads=no — OHOS lacks
    pthread_cancel declaration)

psfex is a command-line tool; the package contains the `psfex` binary.
"""
import os
import re
import glob as _glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PsfexConan(ConanFile):
    name = "psfex"
    version = "3.24.2"
    description = "PSFEx: PSF model building from SExtractor catalogs"
    license = "GPL-3.0-or-later"
    homepage = "https://www.astromatic.net/software/psfex"
    url = "https://github.com/astromatic/psfex"
    exports_sources = "conandata.yml", "patches/*"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def build_requirements(self):
        # GitHub archive tarball 无预生成 configure，需 autoreconf 自举
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        self.requires("fftw3f/3.3.9")
        self.requires("openblas/0.3.34")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["psfex"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        fftw = self.dependencies["fftw3f"]
        blas = self.dependencies["openblas"]
        tc.configure_args.extend([
            # 注意：不加 --build（scamp 同款 config.guess patch 已内联
            # 识别 OHOS——CI 上显式 --build 导致 C compiler works 检查
            # 失败实测（psfex/weightwatcher/skymaker 三库同报））
            "--with-fftw-libdir=%s" % os.path.join(
                fftw.package_folder, "lib"),
            "--with-fftw-incdir=%s" % os.path.join(
                fftw.package_folder, "include"),
            "--enable-openblas",
            "--with-openblas-libdir=%s" % os.path.join(
                blas.package_folder, "lib"),
            "--with-openblas-incdir=%s" % os.path.join(
                blas.package_folder, "include"),
            # plplot 绘图库 OHOS 无——禁用（PSF 建模核心功能不依赖）
            "--enable-plplot=no",
            # OHOS pthread.h 未声明 pthread_cancel（同 swarp 实测）——
            # 禁用多线程（单线程模式完全可用）
            "--enable-threads=no",
        ])
        # 编译期头文件注入（--with-*-incdir 仅 configure 检查阶段生效
        # ——make 编译仍需 -I——同 sextractor 实测）
        tc.extra_cflags.append(
            "-I%s" % os.path.join(fftw.package_folder, "include"))
        tc.extra_cflags.append(
            "-I%s" % os.path.join(blas.package_folder, "include"))
        tc.generate()

    def _patch_ohos_autotools(self):
        """config.guess/config.sub 内联补 OHOS 识别（同 scamp 先例）。

        注意：psfex 源码树同时存在 config/（配置文件目录）与
        autoconf/（AC_CONFIG_AUX_DIR 指向 autoconf——config.guess
        实际所在）——按目录存在性判断会走错分支（实测 config.guess
        未被 patch，HarmonyOS=0）——按 config.guess 文件存在性判断。
        """
        for aux in (os.path.join(self.source_folder, "autoconf"),
                    os.path.join(self.source_folder, "config")):
            if os.path.isfile(os.path.join(aux, "config.guess")):
                break
        cg = os.path.join(aux, "config.guess")
        cs = os.path.join(aux, "config.sub")
        if os.path.isfile(cg):
            text = open(cg, encoding="utf-8", errors="ignore").read()
            changed = False
            if "HarmonyOS" not in text:
                block = (
                    "    *:HarmonyOS:*:*)\n"
                    "\tcase \"$UNAME_MACHINE\" in\n"
                    "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                    "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                    "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                    "\tesac\n"
                    "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                    "\t;;\n\n")
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
            if "ohos-linux" not in text:
                pat = re.compile(
                    r"(?P<ind>^\s*)android-linux\)\n"
                    r"(?P<body>(?:\s*basic_machine=\$field1-unknown\n)?"
                    r"\s*basic_os=linux-android\n"
                    r"\s*;;\n)",
                    re.M)
                m = pat.search(text)
                if m:
                    ind = m.group("ind")
                    new = (
                        m.group(0) +
                        ind + "ohos-linux)\n" +
                        ind + "basic_machine=$field1-unknown\n" +
                        ind + "basic_os=linux-ohos\n" +
                        ind + ";;\n")
                    text = text[:m.start()] + new + text[m.end():]
                    changed = True
            if "gnu* | android* | ohos*" not in text:
                new = text.replace("gnu* | android*",
                                   "gnu* | android* | ohos*")
                changed = changed or new != text
                text = new
            if "linux-ohos" not in text:
                new = text.replace("linux-uclibc* )",
                                   "linux-uclibc* | linux-ohos* )")
                new = new.replace("linux-uclibc*- )",
                                  "linux-uclibc*- | linux-ohos*- )")
                changed = changed or new != text
                text = new
            if changed:
                open(cs, "w", encoding="utf-8").write(text)
                self.output.info("已修补 config.sub: 加入 ohos triplet 支持")

    def build(self):
        os.umask(0)
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if not os.path.isfile(os.path.join(self.source_folder,
                                           "configure")):
            self.output.info("源码树无 configure（GitHub archive），先 autoreconf")
            autotools.autoreconf()
            self._patch_ohos_autotools()
        # OHOS: config.status 临时目录 umask 077 → 000（hmdfs 上失败）
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
        # psfex 是命令行工具，无库文件
