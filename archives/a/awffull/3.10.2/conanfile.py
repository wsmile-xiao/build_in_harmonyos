#!/usr/bin/env python3
"""Conan recipe for awffull 3.10.2 (Web server log analysis tool —
Webalizer fork, autotools).

Dependencies:
  - zlib (compression)
  - libpng (PNG graphs)
  - pcre (regex)
  - gd (graph rendering — hard dependency, configure exits if missing)

sdist includes pre-generated configure (Debian orig).
"""
import os
import re
import glob as _glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AwffullConan(ConanFile):
    name = "awffull"
    version = "3.10.2"
    description = "Web server log analysis tool (Webalizer fork)"
    license = "GPL-3.0-or-later"
    homepage = "http://www.stedee.id.au/awffull"
    url = "https://sources.debian.org/src/awffull/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("libpng/1.6.58")
        self.requires("pcre/8.45")
        self.requires("gd/2.3.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["3.10.2"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        zlib = self.dependencies["zlib"]
        png = self.dependencies["libpng"]
        pcre = self.dependencies["pcre"]
        gd = self.dependencies["gd"]
        tc.configure_args.extend([
            # 注意：不加 --build（旧版 autoconf——CI 上显式 --build 导致
            # C compiler works 失败实测，同 psfex/ats2 系列教训——
            # 依赖 config.guess patch 识别 OHOS）
            "--with-zlib=%s" % os.path.join(zlib.package_folder,
                                            "include"),
            "--with-zliblib=%s" % os.path.join(zlib.package_folder,
                                               "lib"),
            "--with-png=%s" % os.path.join(png.package_folder,
                                           "include"),
            "--with-pnglib=%s" % os.path.join(png.package_folder,
                                              "lib"),
            "--with-pcre=%s" % os.path.join(pcre.package_folder,
                                            "include"),
            "--with-pcrelib=%s" % os.path.join(pcre.package_folder,
                                               "lib"),
            "--with-gd=%s" % os.path.join(gd.package_folder,
                                          "include"),
            "--with-gdlib=%s" % os.path.join(gd.package_folder,
                                             "lib"),
        ])
        # 编译期头文件注入（--with-*-libdir 仅 configure 检查阶段生效
        # ——make 编译仍需 -I——同 sextractor 实测）
        for dep in (zlib, png, pcre, gd):
            tc.extra_cflags.append(
                "-I%s" % os.path.join(dep.package_folder, "include"))
        tc.generate()

    def _patch_ohos_autotools(self):
        """config.guess/config.sub 内联补 OHOS 识别（同 scamp 先例）。"""
        aux = os.path.join(self.source_folder, "config")
        cg = os.path.join(aux, "config.guess")
        cs = os.path.join(aux, "config.sub")
        if os.path.isfile(cg):
            text = open(cg, encoding="utf-8", errors="ignore").read()
            changed = False
            if "HarmonyOS" not in text:
                # config.guess 是旧版（2008-01-23——各分支自行 echo+exit
                # 输出，无统一 echo $GUESS 逻辑，同 skymaker 实测）——
                # 必须用旧版格式插入（新版 GUESS= 变量格式匹配后不输出
                # ——unable to guess system type）
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
                # config.sub 是旧版（2008——无 android-linux 分支，同
                # skymaker 实测）——按旧版格式加 ohos os 支持
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
        # awffull 是命令行工具，无库文件
