#!/usr/bin/env python3
"""Conan recipe for swarp 2.41.5 (FITS image resampling/coaddition tool,
autotools — AstrOmatic suite).

Dependencies:
  - cfitsio/4.6.4 (FITS I/O, published on ohpcd)
  - pthread/libm (system)

swarp is a command-line tool; the package contains the `swarp` binary
and the xsl/swarp.xsl config template.
"""
import os
import re
import glob as _glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SwarpConan(ConanFile):
    name = "swarp"
    version = "2.41.5"
    description = "FITS image resampling and co-addition tool"
    license = "GPL-3.0-or-later"
    homepage = "https://www.astromatic.net/software/swarp"
    url = "https://github.com/astromatic/swarp"
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
        # cfitsio 静态库链接依赖 zlib（deflate 等符号——AC_CHECK_LIB
        # 测试链接需 zlib 路径，否则 CFITSIO library not found 实测）
        self.requires("cfitsio/4.6.4")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["swarp"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        cfitsio = self.dependencies["cfitsio"]
        tc.configure_args.extend([
            "--with-cfitsio-libdir=%s" % os.path.join(
                cfitsio.package_folder, "lib"),
            "--with-cfitsio-incdir=%s" % os.path.join(
                cfitsio.package_folder, "include"),
            # OHOS pthread.h 未声明 pthread_cancel（API 不完整——swarp
            # threads.h 的 QPTHREAD_CANCEL 实测链接失败）——禁用多线程
            # （单线程模式完全可用，scamp 同源处理思路）
            "--enable-threads=no",
        ])
        # 显式注入 zlib 路径与库（cfitsio.a 的传递依赖——AC_CHECK_LIB
        # 测试链接需要 -L 路径 + -lz，否则 CFITSIO library not found 实测）
        zlib = self.dependencies["zlib"]
        tc.extra_ldflags.append(
            "-L%s" % os.path.join(zlib.package_folder, "lib"))
        tc.extra_ldflags.append("-lz")
        tc.generate()

    def _patch_ohos_autotools(self):
        """config.guess/config.sub 内联补 OHOS 识别（同 scamp 先例）。"""
        aux = os.path.join(self.source_folder, "config")
        if not os.path.isdir(aux):
            aux = os.path.join(self.source_folder, "autoconf")
        cg = os.path.join(aux, "config.guess")
        cs = os.path.join(aux, "config.sub")
        # --- config.guess ---
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
        # --- config.sub ---
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
        # swarp 是命令行工具，无库文件
