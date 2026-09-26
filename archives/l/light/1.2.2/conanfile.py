#!/usr/bin/env python3
"""light 1.2.2 — 命令行背光/LED 亮度调节工具（sysfs 后端）。

HarmonyOS PC (aarch64) 适配要点（一手读数见 notes.md）：
  1. Debian .orig 发布树是 autogen 形态：无 configure / aclocal.m4 / Makefile.in /
     config.guess ⇒ 必须先 autoreconf -i 自举。设备与 CI 沙箱的 /data/service/hnp/bin
     只有 autoconf 家族、没有 automake/aclocal（~/usr/local/bin/automake 是断链：
     command -v 找得到、执行报 No such file or directory）⇒ 按 abiword-plugin-* 先例
     把 automake 作为 tool_requires 引入，由 VirtualBuildEnv 注入 PATH。
  2. profile [buildenv] 的 CONFIG_SHELL 会让 autoconf 生成的 configure 无条件
     exec $CONFIG_SHELL 重执行自身，而 hnp bash 5.3 在 conan 构建目录里 getcwd 失败
     （同目录 /bin/sh 正常）⇒ configure 以
     "working directory cannot be determined" 中止。处置见 build()。
  3. configure 尾部自举出的 config.status 用 `(umask 077 && mktemp -d ./confXXXXXX)`
     建临时目录；HMDFS 的 setgid 构建目录下 0700 目录对本进程不可写
     （cat 重定向报 Permission denied）⇒ "could not setup config files machinery"。
     处置：只放宽子进程里的那处 umask（DRAFT-6507/E011 家族的 mkdir 变体轨道；
     本机实测 mktemp 的目录模式跟随 umask，故 022 即可，无需换成 mkdir）。
  4. 上游零外部依赖（configure.ac 只有 AC_PROG_CC/AC_PROG_INSTALL/AC_HEADER_STDC，
     无 PKG_CHECK_MODULES，源码不链接 libudev——实测 dlopen libudev 三个 soname 全失败）
     ⇒ requires() 为空。--with-udev 只决定 make install 是否落一份 udev 规则文件，
     不改动产物；OHOS 实测 /etc/udev 与 /run/udev ENOENT ⇒ 显式 --with-udev=no，
     保持上游 CLASSIC 分支语义。不做编译期平台分叉（R8/PF5 禁平台宏）。
"""
import io
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cmd_args_to_string
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LightConan(ConanFile):
    name = "light"
    version = "1.2.2"
    description = ("The most accurate Linux backlight and LED control utility, "
                   "backed by sysfs (/sys/class/backlight, /sys/class/leds).")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/haikarainen/light"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("backlight", "led", "brightness", "sysfs", "utility")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # 发布树缺全部 autotools 生成件，见模块 docstring 第 1 条。
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-udev=no")
        # clang 11 起默认 -fno-common：上游 helpers.h 里的 `int light_loglevel;` 是
        # tentative definition，于是每个编译单元都在 .bss 里落一份实定义，ld.lld 报
        # "duplicate symbol: light_loglevel"（4 个 .o 各一份，实测见 notes.md）。
        # GCC < 10 的 -fcommon 语义会把 common 符号合并，上游正是依赖该语义发布。
        # 处置：恢复 common 语义，不改上游源码、不注平台宏（R8/PF5）。
        tc.cflags.append("-fcommon")
        tc.generate()
        # 留住 toolchain 合成的完整参数（含 --prefix/--bindir 等），
        # build() 手工调用 configure 时原样复用，绝不手写 prefix。
        self._configure_args = list(tc.configure_args)

    def _configure_script(self):
        for base in (self.build_folder, self.source_folder):
            candidate = os.path.join(base, "configure")
            if os.path.isfile(candidate):
                return candidate
        raise ConanException("configure script not found after autoreconf")

    def _relax_config_status_umask(self, configure):
        """把自举出的 configure（含内嵌 config.status）里的 `umask 077` 放宽为 022。

        生成件由本配方自己 autoreconf 产生、不入仓，故不违反 R6（不改上游生成文件）。
        命中数为 0 时抛错，避免"以为改了其实没改"的静默失效。
        """
        with io.open(configure, encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        hits = text.count("umask 077")
        if hits == 0:
            raise ConanException(
                "generated configure has no 'umask 077' to relax; "
                "the HMDFS config.status fix no longer matches autoconf output")
        with io.open(configure, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text.replace("umask 077", "umask 022"))
        self.output.info("[ohos] relaxed %d 'umask 077' site(s) in generated configure" % hits)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 自举：AM_INIT_AUTOMAKE([1.11 foreign subdir-objects])，树内无 configure。
        autotools.autoreconf(args=["-i"])
        configure = self._configure_script()
        self._relax_config_status_umask(configure)
        # 只对 configure 子进程 POSIX unset CONFIG_SHELL（不是赋空值：空值下
        # configure 前导 SHELL=${CONFIG_SHELL-/bin/sh} 不回退，空 SHELL 被
        # AC_SUBST 进 Makefile ⇒ make 报 "-c: No such file or directory"）。
        # unset 后 configure 不再重执行、留在 /bin/sh 里跑完，getcwd 正常。
        # 轨道沿用仓内 DRAFT-autoconf269-config-shell-unset-not-empty 推荐方案。
        # -fcommon 走 env 通道：conan 生成的 conanbuild.sh 以
        # `export CFLAGS="${CFLAGS:-}${CFLAGS:+ }-O3"` 形式贡献 CFLAGS，
        # configure 把环境 CFLAGS 原样 substituted 进 Makefile 的 @CFLAGS@（实测
        # config.log 内 CFLAGS='-O3'）⇒ 在同一 shell 里追加 -fcommon 必然落到编译行。
        cmd = ("unset CONFIG_SHELL; export CFLAGS=\"${CFLAGS:-} -fcommon\"; "
               + cmd_args_to_string([configure]) + " "
               + cmd_args_to_string(self._configure_args))
        self.run(cmd, cwd=self.build_folder, env="conanbuild")
        # HMDFS 上 make 的 jobserver FIFO 不可靠 ⇒ 固定 -j1。
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 纯可执行交付物，无库/头导出。
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
