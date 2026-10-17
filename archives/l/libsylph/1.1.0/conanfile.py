#!/usr/bin/env python3
"""Conan recipe — libsylph 1.1.0 (E-Mail client library, C/autotools) on HarmonyOS PC.

上游为 2000 年代 autotools 项目，tarball 自带预生成的 configure/aclocal.m4/Makefile.in，
因此**不跑 autoreconf**（新版 glib 不再安装 glib-2.0.m4 / gettext.m4，aclocal 会失败），
只对 config.guess / config.sub 打 OHOS 补丁（见 patches/ 与 notes.md）。
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibsylphConan(ConanFile):
    name = "libsylph"
    version = "1.1.0"
    description = "LibSylph — E-Mail client library derived from Sylpheed"
    license = "LGPL-2.1-or-later"
    homepage = "https://sylpheed.sraoss.jp/"
    url = "https://sylpheed.sraoss.jp/sylpheed/libsylph/libsylph-1.1.0.tar.bz2"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # libsylph 的公共头直接 include <glib.h>，故 glib 必须传递头与库。
        self.requires("glib/2.84.0", transitive_headers=True, transitive_libs=True)
        # AM_GLIB_GNU_GETTEXT 的 po/ 规则在 make 阶段需要 msgfmt/xgettext；
        # glib 的 g_libintl 亦需要 libintl 参与链接（E107/E142）。
        self.requires("gettext/0.22.5", transitive_libs=True, headers=False, libs=False)

    def build_requirements(self):
        # 设备与 CI 均无 pkg-config 二进制；AM_PATH_GLIB_2_0 / PKG_CHECK_MODULES(OPENSSL)
        # 依赖它。ohpcd 制品仓提供 pkgconf（pkg-config 兼容实现）。
        self.tool_requires("pkgconf/3.0.6")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _tool_executable(*names):
        """在 PATH 上按序找第一个可用的工具（跨设备/CI 通用，不硬编码绝对路径）。"""
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return None

    def _dep_tool(self, ref_name, *names):
        """在指定依赖（含 tool_requires）的 package_folder/bin 下按序找工具。"""
        try:
            dep = self.dependencies.build[ref_name]
        except Exception:
            return None
        for name in names:
            cand = os.path.join(dep.package_folder, "bin", name)
            if os.path.isfile(cand):
                return cand
        return None

    def _patch_generated_pcs(self):
        """修 PkgConfigDeps 产物里两处会打断 OHOS 构建的链接接口。

        ① glib/2.84.0 的 package_info() 把 `-L/lib -l:ld-musl-aarch64.so.1` 写进
        链接接口（让链接 glib 的程序带上 musl 动态加载器：OHOS SDK 的 libc.so 缺
        dgettext），PkgConfigDeps 原样落到 glib-2.0.pc 的 Libs: 行；而 /lib 不在
        交叉链接器的搜索路径上 → `ld.lld: error: unable to find library
        -l:ld-musl-aarch64.so.1`。改为绝对路径让 ld.lld 按位置文件引用处理。
        同已合入先例：archives/a/abiword-plugin-openwriter/3.0.8、libgsf/1.14.53。

        ② pcre2 包内 .la 因 `--prefix=/` 而带 `libdir='//lib'`，其 .pc 又是
        `-L<libdir> -lpcre2-8`；libtool 解析该 .la 时去读不存在的
        `//lib/libpcre2-8.la` → `libtool: link: '//lib/libpcre2-8.la' is not a
        valid libtool archive`。把 Libs 换成绝对 .a 路径，libtool 便不再解析 .la。
        路径取自 dependencies，不硬编码（CI 干净环境哈希目录不同）。
        同已合入先例：DRAFT-6048 错误 3 / archives/b/babeltrace/1.5.11、E236。
        """
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.isfile(glib_pc):
            content = open(glib_pc, encoding="utf-8").read()
            if "-l:ld-musl-aarch64.so.1" in content:
                open(glib_pc, "w", encoding="utf-8").write(
                    content.replace("-l:ld-musl-aarch64.so.1",
                                    "/lib/ld-musl-aarch64.so.1"))

        pcre2_pc = os.path.join(self.generators_folder, "pcre2.pc")
        if not os.path.isfile(pcre2_pc):
            return
        try:
            pcre2_lib = os.path.join(self.dependencies.host["pcre2"].package_folder, "lib")
        except Exception:
            return
        archives = [os.path.join(pcre2_lib, name)
                    for name in ("libpcre2-8.a", "libpcre2-posix.a")]
        archives = [p for p in archives if os.path.isfile(p)]
        if not archives:
            return
        lines = open(pcre2_pc, encoding="utf-8").read().splitlines()
        out = []
        for line in lines:
            if line.startswith("Libs:"):
                out.append("Libs: " + " ".join(archives))
            else:
                out.append(line)
        open(pcre2_pc, "w", encoding="utf-8").write("\n".join(out) + "\n")

    def generate(self):
        PkgConfigDeps(self).generate()
        self._patch_generated_pcs()

        tc = AutotoolsToolchain(self)
        # AM_PATH_GLIB_2_0 在非 cross_compiling 下会编译并运行 conftest 读取运行时
        # glib 版本；跳过运行检测，仅保留 pkg-config --atleast-version 校验
        # （同 DRAFT-6048 / archives/b/babeltrace/1.5.11）。
        tc.configure_args.append("--disable-glibtest")
        # libsylph 源码经 glib 的 <glib/gi18n.h> 调用 gettext()，需要 libintl.h 与
        # -lintl：OHOS/musl 不提供系统 libintl，glib 的 g_libintl 仅供其内部使用且
        # 不安装 libintl.h，故由 gettext 依赖提供（E107/E142 家族）。
        # autotools 工具链不会自动把依赖的 cpp_info 注入 CFLAGS/LDFLAGS，
        # 这里显式补上 gettext 的 include/lib。
        # ⚠️ 必须在 tc.environment() **之前** 改这些列表：environment() 会当场
        # 按当前 extra_* 生成 env 快照，之后再 append 不会进入快照。
        gt = self.dependencies.host["gettext"]
        gt_inc = os.path.join(gt.package_folder, "include")
        gt_lib = os.path.join(gt.package_folder, "lib")
        if os.path.isdir(gt_inc):
            tc.extra_cflags.append("-I" + gt_inc)
        if os.path.isdir(gt_lib):
            tc.extra_ldflags.append("-L" + gt_lib)
            tc.extra_ldflags.append("-lintl")
        # OHOS 工具链只提供 ld.lld/lld，**没有名为 `ld` 的链接器**；而
        # `clang -print-prog-name=ld` 返回裸名 `ld`（非路径），libtool 的
        # LT_PATH_LD 探测据此回落到 PATH 检索 → 找不到 → configure 报
        # "no acceptable ld found in $PATH"（本包 AM_PROG_LIBTOOL 必经此步）。
        # 同已合入先例：libXext/6.4.0.1、kstart/4.3、kbd-vlock/2.8.0 的
        # _tool_executable("ld.lld", "lld", "ld")。
        ld = self._tool_executable("ld.lld", "lld", "ld")

        env = tc.environment()
        # AM_PATH_GLIB_2_0 通过 pkg-config 取 GLIB_CFLAGS/GLIB_LIBS，故
        # PKG_CONFIG_PATH **只**指向 PkgConfigDeps 的产物目录（generators_folder）。
        # 切勿把依赖包自带的 lib/pkgconfig 也放进来：依赖自带 .pc 常见
        # `prefix=/`（root 前缀，glib 的 glib-2.0.pc 即如此），一旦它先被命中，
        # Cflags 会被解析成 `-I//include/glib-2.0 -I//lib/glib-2.0/include`
        # → 编译期 "glibconfig.h file not found"。
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # host 依赖的 bin（gettext 的 msgfmt/xgettext 供 po/ 规则调用）；
        # tool_requires(pkgconf) 的 bin 同样要上 PATH。
        for dep in self.dependencies.host.values():
            bin_dir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bin_dir):
                env.prepend_path("PATH", bin_dir)
        for dep in self.dependencies.build.values():
            bin_dir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bin_dir):
                env.prepend_path("PATH", bin_dir)
        # 本仓制品仓的 pkgconf/3.0.x 只装出 `pkgconf` 可执行文件，**没有
        # `pkg-config` 别名**；而 autoconf 的 AC_PATH_TOOL(PKG_CONFIG, pkg-config)
        # 按名检索会落空 → AM_PATH_GLIB_2_0 报 "A new enough version of
        # pkg-config was not found"。故显式把 PKG_CONFIG 指到 pkgconf。
        pkg_config = self._dep_tool("pkgconf", "pkgconf", "pkg-config") \
            or self._tool_executable("pkgconf", "pkg-config")
        if pkg_config:
            env.define_path("PKG_CONFIG", pkg_config)
        if ld:
            env.define_path("LD", ld)
        tc.generate(env=env)
        # OHOS 工具链只提供 ld.lld/lld，**没有名为 `ld` 的链接器**；而
        # `clang -print-prog-name=ld` 返回裸名 `ld`（非路径），libtool 的
        # LT_PATH_LD 探测据此回落到 PATH 检索 → 找不到 → configure 报
        # "no acceptable ld found in $PATH"（本包 AM_PROG_LIBTOOL 必经此步）。
        # 同已合入先例：libXext/6.4.0.1、kstart/4.3、kbd-vlock/2.8.0 的
        # _tool_executable("ld.lld", "lld", "ld")。
        ld = self._tool_executable("ld.lld", "lld", "ld")
        if ld:
            env.define_path("LD", ld)
        tc.generate(env=env)

    def _make_tmpdir(self):
        tmpdir = os.path.join(self.build_folder, "cfg-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    def build(self):
        apply_conandata_patches(self)

        # E011 家族（DRAFT-kexec-tools-2.0.32-mktemp-setgid-2700-hmdfs）：
        # HMDFS 上 (umask 077 && mktemp -d "./confXXXXXX") 产出的目录呈 2700
        # (drwx--S---)，连属主也拒写 → config.status "could not setup config files
        # machinery"。configure 内两处（mktemp 主路径 + mkdir 回退）放宽为 022。
        for name in ("configure",):
            target = os.path.join(self.source_folder, name)
            if os.path.isfile(target):
                replace_in_file(self, target, "umask 077", "umask 022")

        env = Environment()
        env.define_path("TMPDIR", self._make_tmpdir())

        autotools = Autotools(self)
        with env.vars(self).apply():
            autotools.configure()
            # configure 生成的 config.status 会内嵌同一套 mktemp 机制，make 阶段
            # 会被 Makefile 规则重新调用。上面已对 configure 本体放宽，故此处通常
            # 已无 umask 077；仍做一次幂等兜底（同 babeltrace 先例的双保险）。
            cs = os.path.join(self.build_folder, "config.status")
            if os.path.isfile(cs):
                content = open(cs, encoding="utf-8", errors="surrogateescape").read()
                if "umask 077" in content:
                    open(cs, "w", encoding="utf-8", errors="surrogateescape").write(
                        content.replace("umask 077", "umask 022"))
            autotools.make()
            # 上游未提供自动化测试套件（无 tests/、SUBDIRS 不含 check 目标），
            # 仍真实执行 make check 以满足 SKILL §10 并留证（automake 空套件）。
            # 不用 ignore_errors：让 check 成为真实门禁。
            if not cross_building(self):
                autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["sylph"]
        self.cpp_info.includedirs = ["include", "include/sylph"]
        # 引用形式须匹配依赖自身的形态：glib/2.84.0 与 gettext/0.22.5 都是**无组件**
        # 的扁平 cpp_info（glib 只在 package_info 里 set_property pkg_config_name
        # = "glib-2.0"），故用整包形式 `pkg::pkg`；写成 `glib::glib-2.0` 会让
        # CMakeDeps 报 "Component 'glib::glib-2.0' not found"。
        self.cpp_info.requires = ["glib::glib", "gettext::gettext"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
