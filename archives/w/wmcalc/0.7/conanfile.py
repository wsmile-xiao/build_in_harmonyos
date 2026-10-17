#!/usr/bin/env python3
"""Conan recipe — wmcalc 0.7 (WindowMaker 系 X11 dockapp 四则计算器).

上游形态
--------
wmcalc 0.7 是 autoconf 2.69 / automake 发布的 release tarball（configure、
Makefile.in、aclocal.m4、install-sh/compile/depcomp 均已生成，无需
autoreconf）。依赖面一手读 configure.ac：只有三个 ``PKG_CHECK_MODULES``
—— ``x11`` / ``xext`` / ``xpm`` —— 加 ``AC_SEARCH_LIBS([pow], [m])``；
Makefile.am 把这三组 flag 直接吃进 ``AM_CFLAGS``/``LIBS``。故精确依赖 =
libX11 + libXext + libXpm（+ xorgproto 头），**没有为过门禁裁剪任何上游
功能面**（对比同族 asmix/1.5：它当年 libxpm 未发布，只能打补丁剔掉 XPM
图标；本包 libxpm/3.5.17 已发布，XPM 图标全保留）。

W0 依赖证据（2026-09-27，B 机，CONAN_HOME=~/tmp/ch/home-wmcalc，
`conan install --requires=<ref> --build=never -pr:h -pr:b
ci/conan/profiles/ohos-aarch64`，同轮对照包 ncurses/6.5 亦 rc=0）：

    libx11/6.4.0      RC=0   （日志 `Retrieving package ... from remote ohpcd`）
    libxext/6.4.0.1   RC=0   （同上）
    libxpm/3.5.17     RC=0   （同上）
    xorgproto/2025.1  RC=0   （三个 X11 包的传递依赖）
    ncurses/6.5       RC=0   （对照）

依赖轨与已合入的 xeyes/1.3.1、libxpm/3.5.17 一致走 cmd-pkgs 6.4.0 轨
（libxpm 自身 ``force`` libx11/6.4.0；libxext 取最新已发布修订 6.4.0.1）。

OHOS 侧四处必要处置（都不改上游功能语义，全部沿用 CI 已验证的
libXpm/3.5.17 / xeyes/1.3.1 姿势）
------------------------------------------------------------------
1. 交叉模式 ``--build=aarch64-unknown-linux-gnu`` +
   ``--host=aarch64-unknown-linux-ohos``：OHOS 沙箱不能执行刚编出来的
   conftest，native 判定会挂在 "cannot run executables"（E007）。
2. 用 ``/system/bin/sh`` 显式跑 configure/make，并把它 export 成
   ``SHELL``/``CONFIG_SHELL``。profile 的 [buildenv] 把二者设成
   ``/data/service/hnp/bin/bash``，而 autoconf 的 configure 会用
   CONFIG_SHELL 重新解释自己；在 conan 缓存目录下 bash 的
   ``getcwd()`` 不可达（E114/E129，HMBS [shell_getcwd]），configure 顶部
   ``ac_pwd=`pwd` `` 判定直接 "working directory cannot be determined"
   （本机 2026-09-27 create-1.log 第 145 行实拍）。libXpm 的
   ``_run_ohos`` 就是这个处置。
3. ``_generate_ohos_configure()``：在 build_folder 另写一份
   ``configure-ohos``（不动上游文件本身，生成物按 R6 不打补丁），做两件事
   —— ``umask 077`` → ``umask 022``（config.status 临时目录，E114/E129）
   与 ``ac_pwd=`pwd` `` 失败回退 ``$PWD``（HMDFS getcwd）。两处改写都带
   字面命中数校验，命中不符立即抛错，防"静默没打上"。
4. pkg-config 逃逸口：PKG_CHECK_MODULES 展开里有
   ``if test -n "$X11_CFLAGS"`` 分支（wmcalc configure 第 3647 行实拍），
   预置 ``X11_CFLAGS/X11_LIBS``、``XEXT_*``、``XPM_*`` 后 configure 不再
   调用 pkg-config ⇒ 既不需要 pkgconf tool_requires，也不赌各 conan 包
   是否随附 .pc 文件（xeyes 用同一逃逸口；adcli/coturn 先例）。这些变量
   由 **build 环境变量**注入而不是写进 configure 命令行，原因见
   ``_module_flags`` 的 docstring（create-2.log 实拍翻车姿势）。

安装前缀沿用 conan 的 relocatable 姿势（``--prefix=/`` +
``DESTDIR=<package_folder>``），因此 ``AM_CPPFLAGS -DCONF="@sysconfdir@"``
烘进二进制的是 ``/etc``，与上游/发行版语义一致（全局配置
``CONFIGGLOBAL = CONF"/wmcalc.conf"``，用户配置走 ``$HOME/.wmcalc``），
包内 ``etc/wmcalc.conf`` 由管理员按需放置。
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

# PKG_CHECK_MODULES 的宏名前缀 -> 提供该模块的 conan 包
_PKG_MODULES = {
    "X11": "libx11",
    "XEXT": "libxext",
    "XPM": "libxpm",
}

# autoconf 2.69 configure 顶部的工作目录判定（字面针）
_PWD_NEEDLE = 'ac_pwd=`pwd` && test -n "$ac_pwd" &&'
_PWD_FALLBACK = 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"\ntest -n "$ac_pwd" &&'


class WmcalcConan(ConanFile):
    name = "wmcalc"
    version = "0.7"
    description = ("WindowMaker-style X11 dock application calculator "
                   "(64x64 pixmap widget)")
    license = "GPL-2.0-only"
    homepage = "https://www.dockapps.net/wmcalc"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 客户端三件套，全部为 ohpcd 已发布 OHOS armv8 二进制（见模块
        # docstring 的逐条 --build=never rc 与同轮对照包）。xorgproto 提供
        # X11/*.h（xproto/xextproto），由 libx11/libxext 传递，这里显式声明
        # 以便把它的首目录直接写进 *_CFLAGS。
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxpm/3.5.17", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wmcalc supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _dirs(self, package_name, attr):
        """某个 host 依赖的绝对 include/lib 目录列表。"""
        dep = self.dependencies[package_name]
        base = dep.package_folder or ""
        found = []
        for entry in (getattr(dep.cpp_info, attr) or []):
            path = entry if os.path.isabs(entry) else os.path.join(base, entry)
            if os.path.isdir(path) and path not in found:
                found.append(path)
        return found

    def _shell(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        return shell

    def _run_ohos(self, command):
        """在 conan 缓存目录下唯一可靠的执行姿势（libXpm 同款）。"""
        shell = self._shell()
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _module_flags(self):
        """每个 PKG_CHECK_MODULES 前缀对应的 *_CFLAGS / *_LIBS 取值。

        pkg.m4 展开里的逃逸口是 `if test -n "$X11_CFLAGS"`（wmcalc configure
        第 3647 行实拍），且这些变量都由 AC_ARG_VAR 声明 ⇒ 用**环境变量**喂
        而不是写进 configure 命令行：命令行形式 `VAR="a b"` 的引号会被
        config.status 原样烘进 Makefile（本机 create-2.log 实拍：
        `'-I/... -I/...'` 变成一个带引号的单参数，clang 直接忽略，
        随后 `X11/Xlib.h file not found`），环境变量则由 conan 的
        conanbuild.sh 正确加引号、config.status 再按值无引号写入。
        """
        proto_includes = self._dirs("xorgproto", "includedirs")
        flags = {}
        for module, package_name in _PKG_MODULES.items():
            includes = self._dirs(package_name, "includedirs") + proto_includes
            libdirs = self._dirs(package_name, "libdirs")
            libnames = " ".join(
                f"-l{lib}" for lib in (self.dependencies[package_name].cpp_info.libs or []))
            flags[f"{module}_CFLAGS"] = " ".join(f"-I{path}" for path in includes)
            flags[f"{module}_LIBS"] = " ".join(
                [f"-L{path}" for path in libdirs] + [libnames]).strip()
        return flags

    def _build_environment(self):
        temporary = os.path.join(self.build_folder, ".tmp")
        os.makedirs(temporary, exist_ok=True)
        environment = Environment()
        environment.define("TMPDIR", temporary)
        environment.define("SHELL", self._shell())
        environment.define("CONFIG_SHELL", self._shell())
        # HMDFS 上 configure 的 mkdir -p 走 /system/bin 版（libXpm 同款）
        environment.define("MKDIR_P", "/system/bin/mkdir -p")
        for name, value in self._module_flags().items():
            environment.define(name, value)
        return environment

    def _ohos_configure_path(self):
        return os.path.join(self.build_folder, "configure-ohos")

    def _generate_ohos_configure(self):
        """把上游 configure 复制进 build_folder 并按字面校验做两处改写。"""
        upstream = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(upstream):
            raise ConanException(f"configure script is missing: {upstream}")
        with open(upstream, encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        umask_hits = text.count("umask 077")
        if umask_hits != 2:
            raise ConanException(f"configure umask contract changed: {umask_hits}")
        text = text.replace("umask 077", "umask 022")
        if text.count(_PWD_NEEDLE) != 1:
            raise ConanException("configure ac_pwd needle missing")
        text = text.replace(_PWD_NEEDLE, _PWD_FALLBACK, 1)
        generated = self._ohos_configure_path()
        os.makedirs(os.path.dirname(generated), exist_ok=True)
        with open(generated, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    def _autotools_toolchain(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append(f"--srcdir={self.source_folder}")
        for package_name in _PKG_MODULES.values():
            for libdir in self._dirs(package_name, "libdirs"):
                tc.extra_ldflags.append(f"-L{libdir}")
        return tc

    def _configure_ohos(self):
        tc = self._autotools_toolchain()
        arguments = " ".join(shlex.quote(arg) for arg in tc.configure_args)
        self._run_ohos(f'"{self._shell()}" '
                       f'{shlex.quote(self._ohos_configure_path())} {arguments}')

    def _sign_elf(self, path):
        """OHOS 内核拒签未签名 ELF，装包时对 bin/ 逐文件自签（xeyes 同款）。"""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass  # HMDFS chmod 不生效（E046），容错

    # ------------------------------------------------------------------
    def generate(self):
        self._autotools_toolchain().generate()

    def build(self):
        apply_conandata_patches(self)
        self._generate_ohos_configure()
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._configure_ohos()
                self._run_ohos("make -j1")
            else:
                # 非 OHOS（本地 Linux 复核用）保持常规 VPATH 姿势
                from conan.tools.gnu import Autotools
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(args=["-j1"])

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j1 install DESTDIR={destination}")
            else:
                from conan.tools.gnu import Autotools
                Autotools(self).install(args=["-j1"])
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for name in sorted(os.listdir(bin_dir)):
                self._sign_elf(os.path.join(bin_dir, name))
        # 交付面自查：二进制 + 手册页 + 全局配置 + 图标 + desktop 必须都在
        for expected in (
            os.path.join(bin_dir, "wmcalc"),
            os.path.join(self.package_folder, "share", "man", "man1", "wmcalc.1"),
            os.path.join(self.package_folder, "etc", "wmcalc.conf"),
            os.path.join(self.package_folder, "share", "icons", "hicolor",
                         "48x48", "apps", "wmcalc.png"),
            os.path.join(self.package_folder, "share", "applications",
                         "wmcalc.desktop"),
        ):
            if not os.path.isfile(expected):
                raise ConanException(f"packaged file missing: {expected}")

    def package_info(self):
        # 命令行/桌面应用：不导出头文件与链接库（R38 由 commands.json 声明）。
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share", "etc"]
