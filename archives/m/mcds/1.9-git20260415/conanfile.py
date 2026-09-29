#!/usr/bin/env python3
"""Conan recipe — mcds 1.9-git20260415 (Autotools, command-line CardDAV search).

mcds 是 mutt 地址簿的 CardDAV 查询插件：命令行向 CardDAV 服务器发一个
REPORT 请求，把命中的人名/邮箱打到 stdout。上游 https://github.com/t-brown/mcds
（本版本串对应 2026-04-15 的 git 快照提交 0e150e90）。

OHOS aarch64 适配要点（细节与证据见 notes.md）：
- **必须 in-tree 构建**（见 layout() 注释）：automake 给本树生成的
  DEFAULT_INCLUDES 为空，VPATH 下 config.h 找不到（实测 fatal error）。
- 源是 GitHub **提交归档**（git snapshot），仓库不提交 autoreconf 产物，包内
  没有 configure / Makefile.in / config.guess：build() 必须先 `autoreconf -fi`
  自举。构建主机（CI sandbox / 精简 OHOS 镜像）的 PATH 只有
  /data/service/hnp/bin 下的 autoconf+m4，没有 automake/aclocal/libtoolize，
  故 automake/libtool/gettext 一律 tool_requires（adcli、abiword-plugin-*、
  avahi-tools 同族做法）。
- configure.ac 用 AM_GNU_GETTEXT([external]) 而 m4/ 目录不在归档里：aclocal
  必须从 gettext 包的 share/aclocal 取 gettext.m4，autopoint 需要
  gettext_datadir 指到包内数据目录（avahi-tools 同源处理，知识 E337）。
- HMDFS：生成的 configure 里 config.status 以 `umask 077` 建临时目录，落盘成
  2700+setgid 目录后连创建者都写不进去（E114/E011）⇒ configure 运行前文本剥离。
- config.guess 认不出 HarmonyOS（uname -s=HarmonyOS / HongMeng Kernel）⇒ 显式
  传 --build/--host 三元组（config.sub 支持 *-linux-ohos）。
- --disable-nls：po/ 只带 mcds.pot、无任何 .po 翻译，关 NLS 不损失功能，且避免
  libintl 链接（src/gettext.h 的 _() 在 !ENABLE_NLS 下宏化为恒等）。
- --disable-gpgme：configure.ac 在有 GPGME 时强制要求宿主 gpgconf + gpg 可执行
  文件（AC_PATH_PROG 找不到就 AC_MSG_ERROR），构建主机两者皆无。
- --disable-libsecret：制品仓无 libsecret 配方，且其后端是 Secret Service
  D-Bus 接口（OHOS 无 dbus socket）。
- automake 的 maintainer-mode 重生成规则会调用带版本号的 aclocal/automake
  （build-aux/missing 包一层，缺版本号工具即 exit 2）⇒ make/make install 一律
  传 NO_AUTOTOOLS_REGEN 把这些工具变量置为 `:`（知识 E248，见下方常量注释）。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps

# config.guess 无法识别 HarmonyOS，显式给出 autoconf 三元组
# （conan 的 get_gnu_triplet 把 OHOS 映射为 linux-ohos，同一形态）。
TRIPLET = "aarch64-unknown-linux-ohos"


# E248：automake 生成的 Makefile.in 里 ACLOCAL/AUTOMAKE/AUTOCONF/AUTOHEADER/
# MAKEINFO 被展开成 build-aux/missing + **带版本号**的工具名（本树实测为
# aclocal-1.17 / automake-1.17），而 tool_requires 与构建主机 PATH 提供的都是
# **不带版本号**的 aclocal/automake ⇒ missing 找不到就直接 exit 2，configure
# 跑完后 make 仍会去重生成 aclocal.m4 / Makefile / config.h.in 并炸掉
# （实测 make check 报 `Makefile:392: aclocal.m4] Error 127`）。
# 这些是 maintainer-mode 重生成规则，与编译产物无关 ⇒ 一律喂成 shell 空操作 :
# （B 机实测：同一棵已 configure 的树裸 make -n RC=2、喂空变量后 RC=0 且
# 计划命令里出现 clang 编译行）。
NO_AUTOTOOLS_REGEN = [
    "ACLOCAL=:",
    "AUTOCONF=:",
    "AUTOHEADER=:",
    "AUTOMAKE=:",
    "MAKEINFO=:",
]


def _drop_umask_077(conanfile, path):
    """E114/E011：HMDFS 对目录强制 setgid，`(umask 077 && mktemp -d)` 建出来的
    drwx--S--- 临时目录连创建者都不可写，config.status 报
    "can't create ./confXXXXXX/subs1.awk: Permission denied"。
    configure 由 autoreconf 现场生成（归档里没有），无法用 patches/ 交付，
    只能在运行前做文本剥离（adcli / avahi-tools / a52dec 同法）。
    `um(?:ask|ash) 077` 的正则同时覆盖 autoconf 历史拼写笔误 "umash"。"""
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    patched, n_mktemp = re.subn(r"um(?:ask|ash) 077 && mktemp -d", "mktemp -d", text)
    patched, n_mkdir = re.subn(r"um(?:ask|ash) 077 && mkdir", "mkdir", patched)
    if n_mktemp == 0 and n_mkdir == 0:
        conanfile.output.warning(
            "生成的 configure 里没有 AS_TMPDIR 'umask 077' 模式，未施加 HMDFS 规避")
        return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(patched)
    conanfile.output.info(
        "HMDFS umask 077 剥离：mktemp=%d mkdir=%d" % (n_mktemp, n_mkdir))


class McdsConan(ConanFile):
    name = "mcds"
    version = "1.9-git20260415"
    description = ("Command line CardDAV address-book search tool, "
                   "used as a mutt query plugin")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/t-brown/mcds"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac 的两个硬性 PKG_CHECK_MODULES：libcurl（缺省即 AC_MSG_ERROR）、
        # libxml-2.0（解析 carddav-multisearch 响应）。.pc 由 PkgConfigDeps 生成，
        # 两个上游包都已声明 pkg_config_name（curl→libcurl、libxml2→libxml-2.0）。
        self.requires("curl/8.15.0")
        self.requires("libxml2/2.15.3")

    def build_requirements(self):
        # git 归档无 configure ⇒ build() 要 autoreconf；构建主机 PATH 上没有
        # automake/aclocal/libtoolize（只有 SDK 的 autoconf+m4），全部走
        # tool_requires。AM_GNU_GETTEXT 还需要 gettext 的 aclocal 宏与数据目录。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("gettext/0.22.5.1")

    def validate(self):
        # R32：settings.os 必须用 in ("Linux", "OHOS")，不能 == "Linux"
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mcds supports only Linux/OHOS, not " + str(self.settings.os))

    def layout(self):
        # 上游 src/Makefile.am 不设 AM_CPPFLAGS，automake 生成的
        # DEFAULT_INCLUDES 是**空的**（实测 build-release/src/Makefile:140
        # `DEFAULT_INCLUDES =`），#include "config.h" 只能靠"与 main.c 同目录"
        # 这条 quoted-include 规则命中。in-tree 时 config.h 就生成在 src/ 里、
        # 与 main.c 同级 => 正常；VPATH(out-of-tree) 时 main.c 取自 srcdir、
        # config.h 生成在 builddir => 实测 fatal error: 'config.h' file not found。
        # 上游自己的 CI 也只跑 ./configure && make（in-tree），所以这里不
        # 引 basic_layout，把 build 目录压回源码目录。
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        # PKG_CHECK_MODULES(libcurl / libxml-2.0) 的 .pc 由 conan 生成到
        # generators_folder；不把 PKG_CONFIG_PATH 指向依赖包自带的 lib/pkgconfig
        # （包内 .pc 的 prefix 固化了打包机路径）。
        PkgConfigDeps(self).generate()

        env = Environment()
        gettext_pkg = self.dependencies.build["gettext"].package_folder
        gettext_datadir = os.path.join(gettext_pkg, "share", "gettext")
        if os.path.isdir(gettext_datadir):
            env.define("gettext_datadir", gettext_datadir)
        else:
            self.output.warning("gettext 包缺少 share/gettext: " + gettext_datadir)
        gettext_aclocal = os.path.join(gettext_pkg, "share", "aclocal")
        if os.path.isdir(gettext_aclocal):
            env.prepend_path("ACLOCAL_PATH", gettext_aclocal)
        else:
            self.output.warning("gettext 包缺少 share/aclocal: " + gettext_aclocal)
        # profile 的 [buildenv] 把 CONFIG_SHELL/SHELL 指向 hnp bash；该路径在部分
        # 真机不存在（akku 同坑），configure 统一走可用 POSIX shell。
        shell = "/bin/sh" if os.path.exists("/bin/sh") else "sh"
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        env.vars(self).save_script("mcds_bootstrap_env")

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=" + TRIPLET)
        tc.configure_args.append("--host=" + TRIPLET)
        tc.configure_args.append("--disable-dependency-tracking")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-gpgme")
        tc.configure_args.append("--disable-libsecret")
        tc.configure_args.append(
            "PKG_CONFIG_PATH=" + self.generators_folder.replace("\\", "/"))
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        env = ["conanbuild", "mcds_bootstrap_env"]
        # 归档不含 configure：现场生成（NOCONFIGURE 类副作用不存在，
        # autoreconf 本身不会执行 configure）。
        self.run("autoreconf -fi", cwd=self.source_folder, env=env)
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration("autoreconf -fi 未生成 configure")
        _drop_umask_077(self, configure)

        autotools = Autotools(self)
        autotools.configure()
        # E074：并行 make 撞 HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"] + NO_AUTOTOOLS_REGEN)
        # 上游在本提交无任何测试套件（tests/ 目录、TESTS、check_PROGRAMS 全为 0，
        # 清点证据见 test_package/MANIFEST.yml 与 notes.md），故此处没有
        # `make check` 可跑；消费者测试在 test_package/（R34）。

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=NO_AUTOTOOLS_REGEN)
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 纯可执行包：只交付 bin/mcds 与 share/man/man1/mcds.1。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        bin_dir = os.path.join(self.package_folder, "bin")
        self.runenv_info.append_path("PATH", bin_dir)
        self.buildenv_info.append_path("PATH", bin_dir)
