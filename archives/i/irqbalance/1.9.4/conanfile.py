#!/usr/bin/env python3
"""Conan recipe for irqbalance 1.9.4 — IRQ balancing daemon (CLI tools).

Adapted for HarmonyOS PC (aarch64):
- GitHub tag tarball ships no configure: build() 内 autoreconf 自举（tool_requires）
- autoreconf 前修正工具链环境（E007/E136/E490）：
    * PERL5LIB 指向 automake 包 share/automake-<api>（系统 perl 加载 Automake::Config；
      避免 conan perl XS 模块与系统 perl ABI 冲突）
    * ACLOCAL_PATH 含 libtool 宏目录与 pkg.m4（PKG_CHECK_MODULES 展开）
    * _lt_pkgdatadir 指向 libtool 包共享目录 + m4->aclocal 符号链接（libtoolize 可运行）
- autoreconf 后运行期修补：
    * config.guess/sub 注入 HarmonyOS 识别与 linux-ohos triplet（与 patch-autotools-ohos.pl 同锚点）
    * configure umask 077→022 + mktemp 用 $TMPDIR 绝对路径（HarmonyOS config.status 临时目录权限）
- 依赖：glib-2.0（上游强制）、ncursesw（ui）
"""
import os
import re
import glob
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class IrqbalanceConan(ConanFile):
    name = "irqbalance"
    version = "1.9.4"
    description = "irqbalance 1.9.4 — distribute hardware interrupts across processors"
    license = "GPL-2.0-only"
    homepage = "https://github.com/Irqbalance/irqbalance"
    url = "https://github.com/Irqbalance/irqbalance"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.3.1")
        self.requires("ncurses/6.6")

    def build_requirements(self):
        # 系统自带 autoconf 2.72（/data/service/hnp/bin）+ 系统 perl 5.42.0，直接复用；
        # 若 tool_requires 引入 conan autoconf/perl 5.42.2，conanbuildenv 会将
        # AUTORECONF/AUTOM4TE/PERL/PERL5LIB 全线指向 conan perl，而该系统 perl 5.42.0
        # 加载 conan perl 的 XS 模块（Cwd.so）会 ABI 冲突（Perl_my_cxt_init symbol not found）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()
        # PkgConfigDeps：为 glib-2.0 / ncursesw 生成 .pc 并注入 PKG_CONFIG_PATH
        pcd = PkgConfigDeps(self)
        pcd.generate()
        # 工具链环境注入（buildenv_info → conanbuild.sh，autoreconf 子进程继承）
        # 目标：系统 perl 5.42.0 运行 autoreconf 时 @INC 只含 automake 宏目录，
        # 不被 conan perl(5.42.2) 的 XS 模块污染（否则 Cwd.so ABI 冲突）。
        glib_dir = os.path.join(self.dependencies["glib"].package_folder)
        ncurses_dir = os.path.join(self.dependencies["ncurses"].package_folder)
        be = self.buildenv_info
        be.append("PKG_CONFIG_PATH", glib_dir, os.pathsep)
        be.append("PKG_CONFIG_PATH", ncurses_dir, os.pathsep)
        am = self.dependencies.build["automake"]
        lt = self.dependencies.build["libtool"]
        pc = self.dependencies.build["pkgconf"]
        am_share = os.path.join(am.package_folder, "share")
        perl5lib = os.path.join(am_share, "automake-1.18")
        aclocal_path = os.pathsep.join([
            os.path.join(lt.package_folder, "share", "aclocal"),
            os.path.join(pc.package_folder, "share", "aclocal"),
            os.path.join(am_share, "aclocal"),
        ])
        lt_share = os.path.join(lt.package_folder, "share", "libtool")
        lt_m4 = os.path.join(lt_share, "m4")
        if os.path.isdir(lt_share) and not os.path.exists(lt_m4):
            try:
                os.symlink("../aclocal", lt_m4)
            except OSError:
                pass
        be = self.buildenv_info
        be.define("PERL5LIB", perl5lib)
        be.define("ACLOCAL_PATH", aclocal_path)
        be.define("_lt_pkgdatadir", lt_share)
        self.output.info("PERL5LIB=%s" % perl5lib)
        self.output.info("ACLOCAL_PATH=%s" % aclocal_path)
        self.output.info("_lt_pkgdatadir=%s" % lt_share)

    @staticmethod
    def _patch_runtime(root: str) -> None:
        """autoreconf 之后的运行期修补（对生成文件做文本级修改）。"""
        # E007: config.guess 注入 HarmonyOS 识别（与 patch-autotools-ohos.pl 同锚点）
        cg = os.path.join(root, "config.guess")
        if os.path.isfile(cg):
            text = open(cg, encoding="utf-8", errors="ignore").read()
            if "HarmonyOS" not in text:
                block = (
                    "    *:HarmonyOS:*:*)\n"
                    "\tcase \"$UNAME_MACHINE\" in\n"
                    "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                    "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                    "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                    "\t    i?86)         MACHINE=i686 ;;\n"
                    "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                    "\tesac\n"
                    "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                    "\t;;\n"
                )
                if re.search(r"(?m)^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n", text):
                    text = re.sub(
                        r"(?m)^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n",
                        block + "    *:NetBSD:*:*)\n",
                        text,
                        count=1,
                    )
                else:
                    text = text.replace(
                        "    *:GNU:*:*)\n",
                        block + "    *:GNU:*:*)\n",
                    )
            if "LIBC=ohos" not in text and "__OHOS__" not in text:
                text = re.sub(
                    r"(?m)(^\s*#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android)",
                    r"\1\n#elif defined(__OHOS__)\n    LIBC=ohos",
                    text,
                    count=1,
                )
            open(cg, "w", encoding="utf-8").write(text)
            os.chmod(cg, os.stat(cg).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        # E007: config.sub 注入 linux-ohos / ohos-linux
        cs = os.path.join(root, "config.sub")
        if os.path.isfile(cs):
            text = open(cs, encoding="utf-8", errors="ignore").read()
            if "linux-ohos" not in text:
                text = text.replace("linux-gnu*)", "linux-gnu* | linux-ohos*)")
            if "ohos-linux" not in text:
                text = text.replace("nto-qnx* | linux-gnu*", "nto-qnx* | linux-gnu* | linux-ohos*")
                text = text.replace("| -linux-gnu* |", "| -linux-gnu* | -linux-ohos* |")
            open(cs, "w", encoding="utf-8").write(text)
            os.chmod(cs, os.stat(cs).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        # E136: configure umask 077→022 + mktemp 绝对路径（HarmonyOS SGID 临时目录权限）
        for cfg in glob.glob(os.path.join(root, "**", "configure"), recursive=True):
            text = open(cfg, encoding="utf-8", errors="ignore").read()
            if "umask 077" in text:
                text = text.replace("umask 077", "umask 022")
            if 'mktemp -d "./confXXXXXX"' in text:
                text = text.replace(
                    'mktemp -d "./confXXXXXX"',
                    'mktemp -d "${TMPDIR:-/tmp}/confXXXXXX"',
                )
            open(cfg, "w", encoding="utf-8").write(text)
            os.chmod(cfg, os.stat(cfg).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # GitHub tag tarball 无 configure，autoreconf 自举。
        # 使用系统 autoreconf（/data/service/hnp/bin，autoconf 2.72 + 系统 perl 5.42.0）：
        # conan 的 autoconf/perl 工具链（5.42.2）与此环境系统 perl ABI 不兼容
        # （Cwd.so: Perl_my_cxt_init symbol not found），故不从 conan 引入 autoconf。
        self.run("autoreconf --force --install",
                 env="conanbuild", cwd=self.source_folder)
        self._patch_runtime(str(self.source_folder))
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # strip libtool *.la wrappers
        for _la in glob.glob(os.path.join(self.package_folder, "**", "*.la"), recursive=True):
            os.remove(_la)

    def package_info(self):
        # 上游 Makefile.am 用 sbin_PROGRAMS，autotools install 落到 $prefix/sbin
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []