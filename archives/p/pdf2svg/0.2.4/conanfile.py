#!/usr/bin/env python3
"""Conan recipe — pdf2svg 0.2.4（PDF → SVG 转换器，基于 Poppler + Cairo）

上游 configure.ac 用两个 PKG_CHECK_MODULES 声明依赖：

    PKG_CHECK_MODULES(CAIRO,       cairo >= 1.16)
    PKG_CHECK_MODULES(POPPLERGLIB, poppler-glib >= 0.5.4)

本配方**完全不调用 pkg-config**，走 PKG_CHECK_MODULES 自带的 AC_ARG_VAR 逃生口
（生成的 configure 第 3674/3691 行 `if test -n "$CAIRO_CFLAGS"`，第 3766/3783 行
同款 `$POPPLERGLIB_CFLAGS` / `$POPPLERGLIB_LIBS`：两个变量都非空即直接采用，
不再执行 pkg-config）。原因见 notes.md「方案取舍」，一句话版本：

  制品仓里各个依赖包**自带的 .pc 文件记录了构建机的前缀**，把它们的
  `lib/pkgconfig` 放进 PKG_CONFIG_PATH 会让 pkg-config **静默成功**却给出
  错误路径（实测：`cairo.pc` 的 `prefix=/` → `-I/include/cairo -L/lib`；
  `poppler-glib.pc` 的 `prefix=/storage/Users/currentUser/.conan2/p/b/poppl74bba25eec764/p`
  指向另一台构建机的 hash 目录）。错误只是从「configure 找不到模块」后移到
  「编译/链接找不到头文件或库」，更难定位。逃生口 + 由 cpp_info 直接算出
  CFLAGS/LIBS 是最短的、只依赖制品仓真实布局的路径。

上游 0.2.4 **没有测试套件**（tarball 无 tests/ 目录，Makefile.am 只有
bin_PROGRAMS = pdf2svg，无 TESTS/check_PROGRAMS/check-local；meson.build 也不存在），
因此 build() 只跑 configure + make，不做 make check；被测行为全部由
test_package/test_pdf2svg.sh 对**已安装的 bin/pdf2svg** 做端到端断言。

版本号说明：tarball 的 tag 是 v0.2.4，但 configure.ac 里
`AC_INIT(pdf2svg, 0.2.1, ...)` 从未随发布递增（自带的 configure 也是陈旧的
——它还在查 `cairo >= 1.2.6`，而 configure.ac 已改成 1.16）。Conan 包版本按
**tag** 记为 0.2.4，程序自身不打印版本号（无 --version/-V 选项）。
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# PKG_CHECK_MODULES 的两个模块各自对应哪些依赖包的 -I / -L / -l。
# 语义等价于 pkg-config 的传递闭包：
#   cairo.pc         Requires.private: pixman-1 fontconfig freetype2 libpng
#   poppler-glib.pc  Requires: poppler glib-2.0 gobject-2.0 gio-2.0 cairo
# 名字在图里不存在时静默跳过（依赖图变化不应让配方崩），所以多列几个是安全的。
_CAIRO_CLOSURE = ("cairo", "pixman", "fontconfig", "freetype", "libpng")
_POPPLERGLIB_CLOSURE = ("poppler", "glib") + _CAIRO_CLOSURE
# -L 来源（缺一个就会在链接期找不到库）
_CAIRO_LIBDEPS = ("cairo",)
_POPPLERGLIB_LIBDEPS = ("poppler", "glib", "cairo")
# 真正进链接行的 -l（不直接抄 poppler 的 cpp_info.libs：那是
# ['poppler', 'poppler-glib', 'poppler-cpp'] 的根级并集，会白白拖进 poppler-cpp；
# pdf2svg 只 include <poppler.h>/<poppler-document.h>/<poppler-page.h>，即 -lpoppler-glib）
_CAIRO_LIBS = ("cairo",)
_POPPLERGLIB_LIBS = ("poppler-glib", "poppler", "glib-2.0", "gobject-2.0", "gio-2.0")
# 系统库只挂在链接行末尾的 POPPLERGLIB_LIBS 上，避免在两个变量里各出现一份。
_SYSTEM_LIBS = ("m", "pthread", "dl")


class Pdf2svgConan(ConanFile):
    name = "pdf2svg"
    version = "0.2.4"
    description = "PDF to SVG converter based on Poppler and Cairo"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/dawbarton/pdf2svg"
    url = "https://github.com/dawbarton/pdf2svg"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pdf2svg supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # poppler-glib 提供 <poppler.h>/<poppler-document.h>/<poppler-page.h>
        # 与全部 poppler_* 符号；pdf2svg.c 直接 include 它，故 headers 也要传递。
        self.requires("poppler/25.12.0.2", transitive_headers=True, transitive_libs=True)
        # <cairo.h>/<cairo-svg.h> + cairo_* 符号（cairo_show_page 等）。
        # 传传递头：poppler-glib/poppler-page.h 自己也 `#include <cairo.h>`。
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)
        # pdf2svg.c 直接 `#include <glib.h>`，并调用 g_path_is_absolute /
        # g_get_current_dir / g_build_filename / g_filename_to_uri /
        # g_type_init / g_object_unref。glibconfig.h 在
        # <glib>/lib/glib-2.0/include（由 cpp_info 组件提供，见 generate()）。
        self.requires("glib/2.84.0.1", transitive_headers=True)
        # 必须 override：poppler/25.12.0.2 钉 fontconfig/2.18.1，cairo/1.18.4 钉
        # fontconfig/2.18.1.1，两个精确钉死在图里直接撞 version conflict
        # （实测 "Conflict between fontconfig/2.18.1.1 and fontconfig/2.18.1 …
        # originates from cairo/1.18.4"）。取较新的 2.18.1.1：版本默认
        # package_id 模式是 minor_mode，poppler 的 package_id 不变，制品仓里
        # 已发布的 poppler 二进制被原样复用（实测走 Cache，不触发源码重建）。
        self.requires("fontconfig/2.18.1.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 本包 configure.ac 没有 AC_CANONICAL_*，既不跑 config.guess 也不跑
        # config.sub；给一组 (build, host) 相同的本机三元组只是让 host_alias
        # 有值、configure 走 non-cross 分支，同时挡住 profile 在跨机场景下
        # 可能注入的 linux-ohos 三元组（0.2.4 自带的 config.sub 不认 ohos）。
        # 这两个参数不参与任何绕过：不是把 OHOS 伪装成别的系统。
        tc.configure_args.extend(["--build=aarch64-linux", "--host=aarch64-linux"])
        environment = tc.environment()
        # PKG_CHECK_MODULES 的 AC_ARG_VAR 逃生口：四个变量都非空 → configure
        # 直接采用，完全不调用 pkg-config（同 libxp/1.0.4、xauth/1.1.4）。
        environment.define("CAIRO_CFLAGS", self._cflags(_CAIRO_CLOSURE))
        environment.define("CAIRO_LIBS", self._libs(_CAIRO_LIBDEPS, _CAIRO_LIBS))
        environment.define("POPPLERGLIB_CFLAGS", self._cflags(_POPPLERGLIB_CLOSURE))
        environment.define(
            "POPPLERGLIB_LIBS",
            self._libs(_POPPLERGLIB_LIBDEPS, _POPPLERGLIB_LIBS, _SYSTEM_LIBS),
        )
        tc.generate(env=environment)

    def build(self):
        self._patch_configure()

        # HMFS 下 getcwd 不可达（E002/HMBS [shell_getcwd]）：切到 build_folder
        # 并预置 PWD，让 configure 的 `ac_pwd=`pwd`` 兜底有值。
        # 注意 conan 的 Autotools.configure() 不会自己 chdir —— configure 在
        # 进程当前目录执行，所以这里必须显式 chdir 到 build_folder 才是
        # 真正的 out-of-source 构建（同 xauth/1.1.4、xsel/1.2.1）。
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass
        os.environ["PWD"] = self.build_folder
        # config.status 在 HMDFS 下用 umask 077 建临时目录会得到不可执行/不可写
        # 的目录（E002/E114），umask 0 让本次构建进程建出的目录一律可写。
        os.umask(0)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # 上游同时带 COPYING（GPLv2 正文）与 LICENSE（项目声明），两个都收。
        for name in ("COPYING", "LICENSE"):
            copy(
                self,
                name,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
                keep_path=False,
            )
        self._sign_elf(os.path.join(self.package_folder, "bin", "pdf2svg"))

    def package_info(self):
        # 命令行工具：只有 bin/pdf2svg，无可链接库、无可 include 头
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]

    # ── CFLAGS / LIBS 计算（绕过 pkg-config） ────────────────────────
    def _cflags(self, dep_names):
        """按依赖序拼接 -I。

        用 aggregated_components() 而不是根 cpp_info：glib 的
        `include/glib-2.0`、`lib/glib-2.0/include`（glibconfig.h）与
        `include/gio-unix-2.0` 只在组件里，根 cpp_info.includedirs 只有
        `include` 一层，`#include <glib.h>` 会失败。
        """
        flags = []
        for name in dep_names:
            try:
                dependency = self.dependencies[name]
            except KeyError:
                continue
            for path in dependency.cpp_info.aggregated_components().includedirs:
                flag = "-I{}".format(path)
                if flag not in flags:
                    flags.append(flag)
        return " ".join(flags)

    def _libs(self, dep_names, libs, system_libs=()):
        flags = []
        for name in dep_names:
            try:
                dependency = self.dependencies[name]
            except KeyError:
                continue
            for path in dependency.cpp_info.aggregated_components().libdirs:
                flag = "-L{}".format(path)
                if flag not in flags:
                    flags.append(flag)
        flags.extend("-l{}".format(lib) for lib in libs)
        flags.extend("-l{}".format(lib) for lib in system_libs)
        return " ".join(flags)

    # ── configure 的 OHOS 运行期修补（E002 / E114 / HMFS getcwd） ────
    def _patch_configure(self):
        """只改上游自带的 configure，不 autoreconf、不改任何源码。

        tarball 里 configure / Makefile.in / missing / install-sh / depcomp
        配套齐全（AM_INIT_AUTOMAKE([foreign])），所以没有跑 autoreconf 的理由；
        而且 configure 与 configure.ac 的问版本号不一致（configure 里还是
        `cairo >= 1.2.6`），重新生成会把「本包实际生成的 configure 与上游
        tarball 交付物一致」这一前提打破。改动仅两处，都是平台必需：
        """
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        with open(configure_path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        if "umask 077" in text:
            text = text.replace("umask 077", "umask 022")
        if (
            'ac_pwd=`pwd`' in text
            and 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"' not in text
        ):
            text = text.replace(
                'ac_pwd=`pwd`', 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"'
            )
        with open(configure_path, "w", encoding="utf-8") as handle:
            handle.write(text)

    # ── OHOS ELF 签名（E077，同 xauth/xeyes） ───────────────────────
    def _sign_elf(self, path):
        """鸿蒙内核只加载带有效 .codesign 段的 ELF（E077）。

        顺序不可变：先 llvm-objcopy 移除旧签名段 → binary-sign-tool 重新自签名
        → 恢复可执行权限（签名后权限归零）。
        """
        if str(self.settings.os) != "OHOS" or not os.path.isfile(path):
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.exists(sign_tool) and os.path.exists(objcopy)):
            return
        self.run('{} --remove-section .codesign "{}" 2>/dev/null || true'.format(
            shlex.quote(objcopy), path))
        self.run('{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
            shlex.quote(sign_tool), path, path))
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass
