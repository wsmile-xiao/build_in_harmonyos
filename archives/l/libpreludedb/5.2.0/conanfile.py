#!/usr/bin/env python3
"""Conan recipe — libpreludedb 5.2.0 (Prelude SIEM 的 IDMEF 数据库抽象层) on HarmonyOS PC.

libpreludedb 位于 libprelude 之上：把 IDMEF 告警/心跳映射到 SQL 后端（mysql /
pgsql / sqlite3 以 dlopen 插件形式加载），并提供与后端无关的路径选择（selection）
与判据（criteria）解析、classic 格式插件、告警插入与查询 API。上游只发布
autotools 源码。

上游源码地址（见 conandata.yml 说明）：原官网域名已劫持失效、官方 tarball 404，
故锁定 Prelude-SIEM 官方 GitHub 组织的 tag 归档。该归档是 **autoreconf 输入**：
configure / Makefile.in / config.h.in 都没有提交进版本库，所以 build() 必须按上游
autogen.sh 的思路先自举（libtoolize + aclocal + autoconf + autoheader + automake），
再 configure/make。

OHOS 侧的真实障碍（详见 notes.md 与知识图谱）：
  * configure.ac:135 `AM_PATH_LIBPRELUDE(5.2.0, , AC_MSG_ERROR(...), no)` 只认
    **libprelude-config 脚本**（AC_PATH_PROG + 运行编译出的探测程序），而 ohpcd 的
    libprelude/5.2.0 制品按 R38 只交付库（bin/libprelude-config 已剔除）。本配方在
    generate() 里生成一个等价的最小 libprelude-config 兼容层，并把依赖库目录加进
    LD_LIBRARY_PATH，使 libprelude 的 AC_TRY_RUN 探测程序能真正加载 libprelude.so。
  * 上游路径选择语法由 lex/yacc 生成（AC_PROG_LEX / AC_PROG_YACC）→ 需要宿主
    flex/bison（HNP 自带，未纳入 tool_requires）。
  * E007：automake 1.18 自带的 config.guess 不认 `uname -s` = HarmonyOS。
  * E011：HMDFS 下 configure 的 `umask 077` 临时目录不可写 → config.status 失败。
  * 上游 src/Makefile.am 以 `-I$(srcdir)/include` 引用**生成**头
    (preludedb-version.h)，VPATH(out-of-tree) 构建必失败 → 固定 in-tree 布局。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.gnu import Autotools, AutotoolsToolchain

# AM_PATH_LIBPRELUDE 会用到的全部开关（见上游 m4/libprelude.m4）：
#   --thread/--no-thread 切换线程库、--cflags/--pthread-cflags/--ldflags/--libs
#   给出编译链接参数、--version 用于与 prelude_check_version() / 头文件宏对比。
#
# 注意：本模板里**不能**出现行首 `version="..."` 赋值 —— CI 的 L0m 门禁用
# `^\s*version\s*=\s*["\'](...)["\']` 取 conanfile.py 的第一处匹配并与版本目录名比对，
# 模板里的占位赋值会被当成真正的 recipe 版本（实测报
# "版本目录 '5.2.0' 与 conanfile.py version='{version}' 不一致"），故版本值直接内联。
LIBPRELUDE_CONFIG_SHIM = """#!/bin/sh
# 由 libpreludedb/5.2.0 Conan 配方生成的最小 libprelude-config 兼容层。
# AM_PATH_LIBPRELUDE 只认这个脚本；libprelude 制品按 R38 只交付库，故此处按
# libprelude 制品的实际布局复现其输出。
prefix="{prefix}"
libdir="{libdir}"
thread=yes
want_libs=no
want_cflags=no

while test $# -gt 0; do
  case "$1" in
    --prefix)       echo "$prefix" ;;
    --prefix=*)     prefix="${{1#--prefix=}}" ;;
    --exec-prefix)  echo "$prefix" ;;
    --config-prefix) echo "{confdir}" ;;
    --version)      echo "{version}" ;;
    --thread)       thread=yes ;;
    --no-thread)    thread=no ;;
    --cflags)       want_cflags=yes ;;
    --pthread-cflags) thread=yes; want_cflags=yes ;;
    --libs)         want_libs=yes ;;
    --ldflags)      : ;;
    --c++)          : ;;
  esac
  shift
done

if test $want_cflags = yes; then
  echo "{cflags}"
fi

if test $want_libs = yes; then
  echo "-L$libdir -lprelude -lpthread"
fi

exit 0
"""


class LibpreludedbConan(ConanFile):
    name = "libpreludedb"
    version = "5.2.0"
    description = ("LibPreludeDB: the IDMEF database abstraction layer of the Prelude "
                   "SIEM (SQL backends as dlopen plugins, backend-independent "
                   "selection/criteria handling)")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/Prelude-SIEM/libpreludedb"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("prelude", "siem", "idmef", "database")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libpreludedb supports Linux/OHOS only, got {self.settings.os}")
        if not self.options.shared:
            # 上游 configure.ac: AM_DISABLE_STATIC（libtool 只生成 .so）
            raise ConanInvalidConfiguration(
                "libpreludedb upstream is shared-only (configure.ac: AM_DISABLE_STATIC)")

    def requirements(self):
        # 唯一强制第三方依赖：configure.ac:135 AM_PATH_LIBPRELUDE(5.2.0, ...,
        # AC_MSG_ERROR)。MySQL / PostgreSQL / SQLite3 只是可选的 SQL 后端插件
        # （AX_LIB_* 探测不到即自动关闭），SWIG/Python 绑定与 gtk-doc 在
        # generate() 中显式关闭。
        #
        # transitive_headers 必须显式声明：libpreludedb 的**公开头文件**直接
        # #include <libprelude/prelude-inttypes.h> / <libprelude/idmef.h>，而 Conan
        # 对非直接依赖默认 headers=False/libs=False，CMakeDeps 会把传递依赖的
        # INCLUDE_DIRS/LIBS 清空（实测 test_package 报 'libprelude/idmef.h' file
        # not found）。仓库内 461 个配方都按同一约定声明这两个 traits。
        self.requires("libprelude/5.2.0", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # GitHub tag 归档没有 configure/Makefile.in，需要 automake + libtool 自举。
        # autoconf 故意 **不** 声明 tool_requires：与 libprelude/5.2.0 的结论一致 ——
        # ohpcd 的 autoconf 制品与 automake 制品的 perl 依赖互相冲突（.autoreconf-real
        # 用包内 perl + PERL5LIB，.automake-real shebang 写死宿主 HNP perl），混用会在
        # HNP 上炸出 Cwd.so 加载失败；宿主 autoconf 已是 2.72，只用制品补 automake
        # 与 libtool 即可，环境保持自洽。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        # 上游 src/Makefile.am 用 `-I$(srcdir)/include` 引用**生成**头
        # (preludedb-version.h，nodist_include_HEADERS)，VPATH 构建时它只存在于
        # build 树，编译 src/*.c 直接 fatal error: 'preludedb-version.h' file not
        # found。所以本配方固定 in-tree 布局（source == build）。
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = ".conan"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── generate ───────────────────────────────────────────────
    def generate(self):
        VirtualBuildEnv(self).generate()
        self._generate_libprelude_config()

        tc = AutotoolsToolchain(self)
        # 归档没有 configure，AM_MAINTAINER_MODE 默认要求 maintainer 模式
        tc.configure_args.append("--disable-maintainer-mode")
        # 文档与语言绑定需要 gtkdocize/swig，OHOS 上没有这些生成器
        tc.configure_args.append("--disable-gtk-doc")
        tc.configure_args.append("--disable-easy-bindings")
        for opt in ("swig", "python2", "python3"):
            tc.configure_args.append(f"--without-{opt}")
        tc.generate()

    def _dependency_lib_dirs(self):
        dirs = []
        for dep in self.dependencies.host.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            for libdir in dep.cpp_info.aggregated_components().libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(folder, libdir)
                if os.path.isdir(path) and path not in dirs:
                    dirs.append(path)
        return dirs

    def _generate_libprelude_config(self):
        """生成 libprelude-config 兼容层（AM_PATH_LIBPRELUDE 的唯一入口）。

        upstream 的 m4/libprelude.m4 走的是 autoconf 老套路：先用 AC_PATH_PROG 找
        libprelude-config 脚本，再用脚本的 --version/--cflags/--libs 编译并**运行**
        一段探测程序（AC_TRY_RUN），比对 prelude_check_version(NULL)、头文件宏与脚本
        版本三者一致。因此这里既要提供脚本，也要让探测程序在运行期找得到
        libprelude.so 及其 gnutls 依赖链（这些制品以 shared=False 发布却只含 .so，
        Conan 不会替下游注入 LD_LIBRARY_PATH）。
        """
        dep = self.dependencies["libprelude"]
        components = dep.cpp_info.aggregated_components()
        prefix = dep.package_folder
        libdirs = [d if os.path.isabs(d) else os.path.join(prefix, d)
                   for d in components.libdirs]
        incdirs = [d if os.path.isabs(d) else os.path.join(prefix, d)
                   for d in components.includedirs]

        bindir = os.path.join(self.build_folder, ".dependency-prefix", "bin")
        os.makedirs(bindir, exist_ok=True)
        shim = os.path.join(bindir, "libprelude-config")
        with open(shim, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(LIBPRELUDE_CONFIG_SHIM.format(
                prefix=prefix,
                libdir=libdirs[0] if libdirs else os.path.join(prefix, "lib"),
                version=dep.ref.version,
                cflags=" ".join(f"-I{d}" for d in incdirs),
                confdir=os.path.join(prefix, "etc", "prelude"),
            ))
        os.chmod(shim, 0o755)

        env = Environment()
        env.define("LIBPRELUDE_CONFIG", shim)
        # PATH / LD_LIBRARY_PATH 必须用 append_path（按 os.pathsep 连接）：append()
        # 的默认分隔符是空格，会拼出 "<旧值> <dir1> <dir2>" 这种动态链接器与 shell
        # 都不认识的值 —— 实测该错误让 libprelude 的 AC_TRY_RUN 探测程序直接起不来
        # （"The test program compiled, but did not run"），configure 误判依赖缺失。
        env.append_path("PATH", bindir)
        for libdir in self._dependency_lib_dirs():
            env.append_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuildenv-libpreludedb")
        self.output.info(f"[libprelude-config] 兼容层已生成: {shim}")

    # ── bootstrap the missing autoreconf output ────────────────
    def _bootstrap_autotools(self):
        src = self.source_folder
        if os.path.isfile(os.path.join(src, "configure")):
            self.output.info("configure 已存在，跳过自举")
            return
        # 等价上游 autogen.sh（gnulib-tool / gtkdocize 不需要：libmissing/ 与
        # m4/gtk-doc.m4 + gtk-doc.make 都已随归档提交）。上游 autogen.sh 给
        # libtoolize 传了 --ltdl，但本树 configure.ac 里没有 LT_CONFIG_LTDL_DIR /
        # LTDL_INIT，用的是递归 libtool 模式，故不带 --ltdl（同时也避开 E429：
        # ohpcd 的 libtool 制品把独立 libltdl 放在 share/libtool/ 而不是
        # share/libtool-conan/libltdl，libtoolize --ltdl 会返回 1）。
        self.run('"${LIBTOOLIZE:-libtoolize}" -c --force --automake',
                 cwd=src, env="conanbuild", ignore_errors=True)
        for cmd in ("aclocal -I m4 -I libmissing/m4", "autoconf", "autoheader",
                    "automake --add-missing --copy --foreign"):
            self.run(cmd, cwd=src, env="conanbuild")

    def _patch_config_guess_for_ohos(self):
        """E007：给自举出来的 config.guess 补 HarmonyOS 识别。

        automake 1.18 自带的 config.guess（FSF 2024-07-27）里没有 HarmonyOS 分支，
        `uname -s` = HarmonyOS 时直接 "cannot guess build type"。按 E007 的铁律不能
        用 --build/--host 伪造三元组绕过（那会让 configure 认定交叉编译，跳过全部
        AC_RUN_IFELSE 探测、生成与平台不符的 config.h），改为注入 case 分支，输出
        标准三元组 aarch64-unknown-linux-ohos。同版本的 config.sub 已认识 `linux-*`，
        无需再补 ohos 分支。
        """
        block = ('    *:HarmonyOS:*:*)\n'
                 '\tGUESS=$UNAME_MACHINE-unknown-linux-ohos\n'
                 '\t;;\n\n'
                 '    *:NetBSD:*:*)')
        patched = []
        for script in ("config.guess", os.path.join("build-aux", "config.guess")):
            path = os.path.join(self.source_folder, script)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="surrogateescape") as handle:
                text = handle.read()
            if "HarmonyOS" in text:
                continue
            if "    *:NetBSD:*:*)" not in text:
                self.output.warning(f"{script} 里找不到 HarmonyOS 注入锚点，跳过")
                continue
            text = text.replace("    *:NetBSD:*:*)", block, 1)
            with open(path, "w", encoding="utf-8", newline="\n",
                      errors="surrogateescape") as handle:
                handle.write(text)
            os.chmod(path, 0o755)
            patched.append(script)
        self.output.info(f"[E007] config.guess 已支持 HarmonyOS: {patched}")

    def _relax_configure_umask(self):
        """E011：HMDFS 下 configure 的 `umask 077` 建出的临时目录不可写。

        config.status 往 `(umask 077 && mktemp -d ./confXXXXXX)` 里写 subs1.awk 会被
        拒绝（HMDFS 的 UID 映射让 0700 目录对当前进程也不开放写权限），报
        "could not setup config files machinery"。与 ncdc/bsdtar 等配方一致，把
        configure 里的 umask 077 放宽成 022。
        """
        path = os.path.join(self.source_folder, "configure")
        with open(path, encoding="utf-8", errors="surrogateescape") as handle:
            text = handle.read()
        hits = text.count("umask 077")
        if hits:
            with open(path, "w", encoding="utf-8", newline="\n",
                      errors="surrogateescape") as handle:
                handle.write(text.replace("umask 077", "umask 022"))
        self.output.info(f"[E011] configure umask 077→022: {hits} 处")

    # ── build ──────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        self._bootstrap_autotools()
        self._patch_config_guess_for_ohos()
        self._relax_configure_umask()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

        # 上游测试入口：vendored gnulib（libmissing/tests）的 libc/kernel 自检，
        # 由 automake parallel-tests 驱动（TESTS/check_PROGRAMS）。必须 cd 进该目录
        # 执行：从父目录 `make -C libmissing/tests check` 会让 libtool wrapper 的
        # getcwd 解析失败（HMDFS）。上游本包没有自己的 tests/ 目录（已核验）。
        self.run("make check", cwd=os.path.join(self.build_folder, "libmissing", "tests"),
                 env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 库包只交付 .so / 头文件 / dlopen 插件模块 / aclocal 宏：libtool 归档元数据
        # 在制品间不可重定位；bin/ 下的 preludedb-admin（Perl 运维脚本）、
        # libpreludedb-config（已被 pkg-config 取代）属于 Prelude 服务器侧的运维工具，
        # 不进库包（R38：库类型不需要 commands.json）。
        for folder in ("bin", "share/man"):
            shutil.rmtree(os.path.join(self.package_folder, folder), ignore_errors=True)
        for root, _, files in os.walk(self.package_folder):
            for name in files:
                if name.endswith(".la"):
                    os.remove(os.path.join(root, name))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["preludedb"]
        # 上游头文件装在 $(prefix)/include/libpreludedb，源码以 <libprelude/...> /
        # <preludedb.h> 两种形式包含
        self.cpp_info.includedirs = ["include/libpreludedb", "include"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("pkg_config_name", "libpreludedb")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        # libpreludedb.so 的 DT_NEEDED 里有 libprelude.so 及其 gnutls 依赖链，但 Conan
        # 不会自动把它们带进下游 LD_LIBRARY_PATH：ohpcd 的 gnutls 制品以 option
        # shared=False 发布、包内却只有 .so，require.run 为 False；libprelude/5.2.0
        # 制品同理。这里按“目录里真的有 .so”补运行环境，否则下游一加载
        # libpreludedb.so 就报 Error loading shared library libprelude.so.28。
        for dep in self.dependencies.host.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            for libdir in dep.cpp_info.aggregated_components().libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(folder, libdir)
                if not os.path.isdir(path):
                    continue
                if any(name.endswith(".so") or ".so." in name for name in os.listdir(path)):
                    self.runenv_info.append_path("LD_LIBRARY_PATH", path)
