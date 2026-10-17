#!/usr/bin/env python3
"""Conan recipe — libgda5 5.2.10 (GNU Data Access 5) for HarmonyOS PC.

libgda 是 GLib/GObject 之上的数据库抽象层：连接管理、SQL 解析、数据模型、
provider 插件（sqlite/mysql/postgres/...）。5.x 分支是 autotools 构建，
与 6.x（meson）不是同一代配方。

构建形态（上游默认值 + OHOS 现实约束，逐项见 notes.md）：
  providers   : SQLite（--enable-system-sqlite）
  关闭         : mysql/postgres（见 notes：mysql-client 与 glib 存在 zlib
                版本硬冲突、postgres 需 pg_config）、libsecret/libsoup/bdb/
                oracle/ldap/firebird/mdb/java/gnome-keyring/UI/gdaui-gi/
                crypto/gtk-doc
  tools       : --disable-tools —— tools/cmdtool (gda-sql) 依赖
                AC_CHECK_LIB(ncurses) 命中 libncurses.so，而 ncurses/6.6 包
                只提供静态 libncursesw.a（R4：ncurses 共享库在 OHOS 会破坏
                系统），探测失败后上游行为是静默不构建 cmdtool。
  glib        : 必须用 **shared** 变体（glib/2.88.3 默认 shared=True）。
                glib 在制品仓只有 glib2/2.88.0 是静态-only；静态 glib 会被
                打进 libgda-5.0.so（-export-symbols-regex 隐藏），导致
                libgda 与消费者各持一份 GObject 类型系统 → 上游测试大面积
                崩溃（见 notes.md 实测记录）。
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps


class Libgda5Conan(ConanFile):
    name = "libgda5"
    version = "5.2.10"
    description = "GNU Data Access 5 — GLib/GObject based database abstraction library"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgda"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "with_vala": [True, False]}
    # glib 必须取 shared 变体：静态 glib 会被 libgda 的版本脚本隐藏符号后
    # 内嵌进 libgda-5.0.so，消费者侧会出现两套 GObject 类型系统（见 notes.md）。
    default_options = {"shared": True, "with_vala": False, "glib/*:shared": True}

    # configure.ac:164-170 逐个探测 glib 子模块；PkgConfigDeps 只保证聚合
    # glib-2.0.pc 存在（部分 glib 配方不导出组件 .pc），缺失的按 glib 前缀派生。
    # (pkg-config 名, 该模块对应的库名)
    _GLIB_SUB_PCS = (
        ("gobject-2.0", "gobject-2.0"),
        ("gthread-2.0", "gthread-2.0"),
        ("gmodule-2.0", "gmodule-2.0"),
        ("gmodule-no-export-2.0", "gmodule-2.0"),
        ("gio-2.0", "gio-2.0"),
        ("gio-unix-2.0", "gio-2.0"),
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"

    def requirements(self):
        # 直接依赖：COREDEPS(glib+libxml2) / libxslt(libgda-xslt,report) /
        # sqlite3(provider) / iso-codes(ISO 4217 数据)
        self.requires("glib/2.88.3")
        # libxml2 版本与 libxslt/1.1.45.2 的 pin 对齐（libxslt 声明 2.15.3）
        self.requires("libxml2/2.15.3")
        self.requires("libxslt/1.1.45.2")
        self.requires("iso-codes/4.20.1")

    def build_requirements(self):
        # 构建期工具：pkg-config 提供者、po/ 国际化（IT_PROG_INTLTOOL）
        self.tool_requires("pkgconf/3.0.6")
        self.tool_requires("intltool/0.51.0")
        if self.options.with_vala:
            self.tool_requires("vala/0.56.19")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        # ⚠️ 不要用 AutotoolsDeps：它会把所有宿主依赖的 -l 塞进 LIBS/LDFLAGS，
        # configure 早期的 conftest（能否运行编译产物）也会链上 glib.so 等
        # 共享库，而构建期 LD_LIBRARY_PATH 里没有 conan 包路径 → 运行返回 127，
        # configure 误判 "cannot run C compiled programs"。libgda 的链接标志
        # 全部来自 pkg-config（各依赖 .pc 的 Libs），无需 AutotoolsDeps。
        self._derive_missing_glib_pcs()
        self._relocate_pcre2_libs()

        tc = AutotoolsToolchain(self)
        # 上游 tarball 内的 config.guess 是 2018-02-24 版，不认识
        # `uname -s = HarmonyOS`（报 "cannot guess build type"），因此显式给出
        # build/host 三元组（同 goffice 配方的处理方式）；host==build ⇒ 非交叉编译。
        arch = {"armv8": "aarch64", "x86_64": "x86_64"}.get(str(self.settings.arch),
                                                           str(self.settings.arch))
        tc.configure_args += [
            # libgda 把 DATADIR/providers 目录编译进库。conan 的 autotools
            # 安装用 DESTDIR=package_folder（configure 记录 prefix=/），编译期
            # 路径会变成 /share、/lib/libgda-5.0/providers → 运行期找不到
            # provider（"No provider 'SQLite' installed"）。开启 binreloc，让
            # libgda 运行期从自身 .so 路径推导前缀，包可重定位。
            "--enable-binreloc",
            f"--build={arch}-linux",
            f"--host={arch}-linux",
            # SQLite：用 libgda 自带的内嵌 sqlite（上游 fallback 路径）。
            # 不能开 --enable-system-sqlite：libgda 5.x 的 SQLite provider 通过
            # g_module_open("libsqlite3.so") 在**运行期**加载 sqlite 库
            # （libgda/sqlite/gda-symbols-util.c:110），而制品仓的 sqlite3 包
            # 只提供静态 libsqlite3.a（R26 系统同名库策略）→ provider 无法实例化
            # （"Can't find libsqlite3.so file." → "Can't instantiate provider
            # 'SQLite'"），所有需要数据库连接的测试全部无法运行。内嵌模式定义
            # STATIC_SQLITE，provider 直接注册 GType，无需 dlopen。
            "--disable-system-sqlite",
            "--without-libsecret",
            "--without-libsoup",
            "--without-bdb",
            "--without-oracle",
            "--without-ldap",
            "--without-firebird",
            "--without-mdb",
            "--without-java",
            "--without-gnome-keyring",
            "--without-ui",
            "--disable-gdaui-gi",
            "--disable-crypto",
            "--disable-tools",
            # 注意：这里**不能**传 --disable-introspection。upstream 的
            # configure.ac:494 用 `test x$found_introspection != xyes`（未加引号）
            # 判断，而 --disable-introspection 会让该变量取带空格的字符串
            # "no (disabled, use --enable-introspection to enable)" → test 参数
            # 个数错误 → disable_gda_gi 不会被置位 → ENABLE_GDA_GI 恒为真，
            # 但 INTROSPECTION_MAKEFILE 为空 ⇒ make 报
            # "No rule to make target 'Gda-5.0.typelib'"。
            # 保持默认 auto：OHOS 侧没有 gobject-introspection-1.0.pc，auto 得到
            # 无空格的 "no"，条件判断正常，introspection 干净关闭。
            "--disable-gtk-doc",
            # HMDFS 上 depcomp 的依赖跟踪不可靠（同 goffice 配方结论）
            "--disable-dependency-tracking",
        ]
        tc.configure_args.append("--enable-vala" if self.options.with_vala else "--disable-vala")

        # gettext 的 ngettext 声明：glib 的 gi18n-lib.h 只 include <libintl.h>，
        # 而 OHOS sysroot 的 /usr/include/libintl.h 没有 ngettext 声明 →
        # gda-data-model.c:2982 报 "call to undeclared function 'ngettext'"。
        # glib 静态包（glib2/2.88.0）自带 proxy libintl.h；glib 共享包
        # （glib/2.88.3）没有 → 此时注入等价的本地 shim（映射到 glib 自带的
        # g_dgettext/g_dngettext）。
        # ⚠️ 必须在 tc.environment() 之前 append：environment() 会把当时的
        # cflags 快照进 env，之后再改 extra_cflags 不会生效。
        glib_include = self._dep_include_dir("glib", "libintl.h")
        intl_include = glib_include or self._ensure_libintl_shim()
        if intl_include:
            tc.extra_cflags.append(f"-I{intl_include}")

        env = tc.environment()
        # 干净环境可能没有 pkg-config 可执行文件：用 conan 的 pkgconf 工具包补位
        pkgconf = self._tool_binary("pkgconf", "pkgconf")
        if pkgconf:
            env.define("PKG_CONFIG", pkgconf)
        # OHOS SDK 把 gettext 工具拆成两个目录：/data/service/hnp/bin 只有
        # xgettext/msgfmt，msgmerge 在 gettext.org/<ver>/bin。configure 的
        # IT_PROG_INTLTOOL 检查要求 msgmerge，否则直接报
        # "GNU gettext tools not found; required for intltool"。
        for gettext_bin in sorted(glob.glob("/data/service/hnp/gettext.org/*/bin")):
            env.prepend_path("PATH", gettext_bin)
        # IT_PROG_INTLTOOL 还会执行 perl 的 require XML::Parser 检查，OHOS 侧
        # perl 无该 CPAN 模块（且 XS 模块无法在 HMDFS 上 dlopen），注入最小 stub。
        env.prepend_path("PERL5LIB", self._ensure_perl_stub())
        # gtk-doc/yelp 的 YELP_HELP_INIT 检查是**无条件**执行的：即便
        # --disable-gtk-doc 也要求 PATH 上有 itstool 与 xmllint。xmllint 由 OHOS
        # SDK 提供；itstool 在 OHOS 侧不存在，而 --disable-gtk-doc 下 yelp 文档
        # 规则被门控（configure.ac:623-636）不会执行，故放 stub 让探测通过。
        env.prepend_path("PATH", self._ensure_tool_stub("itstool"))
        # providers/*/specs 的 .xml 由 intltool-merge -x 生成，XML 模式必须依赖
        # perl XML::Parser（OHOS 无该模块）。放一个只做「剥离 intltool 标记」的
        # shim 并显式指定给 configure（AC_PATH_PROG 见 INTLTOOL_MERGE 已设置即
        # 直接采用），避免命中 conan intltool 包里的真工具。
        env.define("INTLTOOL_MERGE", self._ensure_intltool_merge_shim())
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        glib_bin = self._glib_tool_bin()
        if glib_bin:
            # libgda 的 Makefile.am 以裸命令调用 glib-mkenums（没有 make 变量可
            # 覆盖），而 OHOS 自带 glib-mkenums(2.38.2) 的 shebang 指向不存在的
            # /usr/bin/perl（Error 126）。这里在 shell 命令里给 PATH 加前缀：
            # conan 的 build 环境先应用，`$PATH` 由 shell 展开后再叠加 glib 工具
            # 目录 —— profile 的 [buildenv] PATH 前置项优先级高于 generate() 里的
            # env.prepend_path，因此只能这样覆盖（同 libgda6 配方的 PATH 处理）。
            jobs = self.conf.get("tools.build:jobs", default=os.cpu_count() or 2, check_type=int)
            self.run(f'PATH="{glib_bin}:$PATH" make -j{jobs}', env="conanbuild")
        else:
            autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING.LIB", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libgda-5.0")
        self.cpp_info.set_property("cmake_target_name", "libgda-5.0::libgda")
        self.cpp_info.set_property("pkg_config_name", "libgda-5.0")
        self.cpp_info.libs = ["gda-5.0", "gda-report-5.0", "gda-xslt-5.0"]
        # 与上游 libgda-5.0.pc 的 Cflags 对齐：头文件在
        # include/libgda-5.0/libgda/ 下（如 <sql-parser/…> 是相对 libgda/ 解析的），
        # 因此两个目录都要暴露给消费者。
        self.cpp_info.includedirs = ["include/libgda-5.0", "include/libgda-5.0/libgda"]
        self.cpp_info.requires = [
            "glib::glib",
            "glib::gobject",
            "glib::gthread",
            "glib::gmodule",
            "glib::gio",
            "libxml2::libxml2",
            "libxslt::libxslt",
            # iso-codes 是纯数据依赖（ISO 4217 等），没有库；这里显式声明以保持
            # conan 的直接依赖一致性检查通过（运行时通过 ISO_CODES_PREFIX 数据）。
            "iso-codes::iso-codes",
        ]

    # ------------------------------------------------------------------ #
    #  helpers                                                            #
    # ------------------------------------------------------------------ #
    def _relocate_pcre2_libs(self):
        """把 pcre2 的静态库/.la 复制到构建私有目录并改写 .la 的 libdir。

        pcre2 包的 libpcre2-8.la 内是 `libdir='//lib'`（打包时 prefix=/ 被硬化），
        libtool 链接时报
        "libtool: error: cannot find the library '//lib/libpcre2-8.la'"。
        复制 + 改写 libdir（含 libpcre2-posix.la 的 dependency_libs），并让生成的
        pcre2.pc 指向该目录。
        """
        dep = self.dependencies.get("pcre2")
        if dep is None or not dep.package_folder:
            return
        src_lib = os.path.join(dep.package_folder, "lib")
        if not os.path.isdir(src_lib):
            return
        dst_lib = os.path.join(self.build_folder, "pcre2-reloc", "lib")
        os.makedirs(dst_lib, exist_ok=True)
        for name in os.listdir(src_lib):
            if name.startswith("libpcre2"):
                shutil.copy2(os.path.join(src_lib, name), os.path.join(dst_lib, name))
        for name in os.listdir(dst_lib):
            if not name.endswith(".la"):
                continue
            la_path = os.path.join(dst_lib, name)
            content = load(self, la_path)
            content = re.sub(r"^libdir='[^']*'", f"libdir='{dst_lib}'", content, flags=re.M)
            content = content.replace("//lib/", dst_lib + "/")
            save(self, la_path, content)
        pc_path = os.path.join(self.generators_folder, "pcre2.pc")
        if os.path.exists(pc_path):
            content = load(self, pc_path)
            content = content.replace("${prefix}/lib", dst_lib)
            save(self, pc_path, content)
        self.output.info(f"[libgda5] pcre2 libs relocated -> {dst_lib}")

    def _derive_missing_glib_pcs(self):
        """按 glib-2.0.pc 的真实前缀补出缺失的 glib 子模块 .pc。

        configure.ac 的 COREDEPS 逐个 PKG_CHECK_MODULES gobject-2.0/
        gthread-2.0/gmodule-no-export-2.0，PkgConfigDeps 若未导出这些组件
        （或未导出 no-export 变体）会让 configure 直接报错。
        """
        gen = self.generators_folder
        base = os.path.join(gen, "glib-2.0.pc")
        if not os.path.exists(base):
            return
        content = load(self, base)
        prefix = self._pc_variable(content, "prefix") or "${pcfiledir}/../.."
        cflags = self._pc_variable(content, "Cflags") or "-I${includedir} -I${includedir1}"
        for name, lib in self._GLIB_SUB_PCS:
            dst = os.path.join(gen, name + ".pc")
            if os.path.exists(dst):
                continue
            save(
                self,
                dst,
                (
                    "prefix={prefix}\n"
                    "libdir=${{prefix}}/lib\n"
                    "includedir=${{prefix}}/include/glib-2.0\n"
                    "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                    "\n"
                    "Name: {name}\n"
                    "Description: glib sub-module {name} (derived by libgda5 recipe)\n"
                    "Version: 2.88.3\n"
                    "Libs: -L${{libdir}} -l{lib}\n"
                    "Cflags: {cflags}\n"
                    "Requires: glib-2.0\n"
                ).format(prefix=prefix, name=name, lib=lib, cflags=cflags),
            )
            self.output.info(f"[libgda5] derived {name}.pc (prefix={prefix})")

    @staticmethod
    def _pc_variable(content, var):
        match = re.search(r"^{}\s*=\s*(.+)$".format(var), content, re.M)
        return match.group(1).strip() if match else ""

    def _ensure_libintl_shim(self):
        """生成 libintl.h shim（glib 包不带 proxy libintl.h 时使用）。

        glib 2.88 的 gi18n-lib.h 只 `#include <libintl.h>`，但 OHOS sysroot 的
        /usr/include/libintl.h 是残桩，没有 ngettext 声明。glib 自身提供
        g_dgettext/g_dngettext，本 shim 把 gettext 家族映射过去。返回 include 目录。
        """
        shim_dir = os.path.join(self.build_folder, "intl-shim")
        os.makedirs(shim_dir, exist_ok=True)
        header = os.path.join(shim_dir, "libintl.h")
        if not os.path.isfile(header):
            save(self, header, (
                "/* libintl.h shim for HarmonyOS: glib 提供 gettext 实现，\n"
                " * 而 OHOS sysroot 的 libintl.h 缺少 ngettext 声明。 */\n"
                "#ifndef LIBGDA5_LIBINTL_SHIM_H\n"
                "#define LIBGDA5_LIBINTL_SHIM_H\n"
                "#include <glib.h>\n"
                "#define gettext(String) g_dgettext (GETTEXT_PACKAGE, String)\n"
                "#define dgettext(Domain, String) g_dgettext (Domain, String)\n"
                "#define ngettext(String, StringP, N) "
                "g_dngettext (GETTEXT_PACKAGE, String, StringP, N)\n"
                "#define dngettext(Domain, String, StringP, N) "
                "g_dngettext (Domain, String, StringP, N)\n"
                "#define textdomain(Domain) ((char *) (Domain))\n"
                "#define bindtextdomain(Domain, Dirname) ((char *) (Domain))\n"
                "#define bind_textdomain_codeset(Domain, Codeset) ((char *) (Codeset))\n"
                "#endif\n"
            ))
            self.output.info(f"[libgda5] libintl.h shim -> {shim_dir}")
        return shim_dir

    def _ensure_perl_stub(self):
        """注入最小 XML::Parser stub（PERL5LIB），供 IT_PROG_INTLTOOL 的
        perl require 检查使用。返回 stub 的 lib 目录。"""
        stub_lib = os.path.join(self.build_folder, "perl-stub-lib")
        xml_dir = os.path.join(stub_lib, "XML")
        os.makedirs(xml_dir, exist_ok=True)
        parser = os.path.join(xml_dir, "Parser.pm")
        if not os.path.isfile(parser):
            save(self, parser, "package XML::Parser;\nour $VERSION = '2.44';\n1;\n")
            self.output.info(f"[libgda5] perl XML::Parser stub -> {stub_lib}")
        return stub_lib

    def _ensure_intltool_merge_shim(self):
        """生成 intltool-merge 替代脚本（剥离 intltool 的 `_` 翻译标记）。

        XML 模式下真正的 intltool-merge 需要 perl XML::Parser，OHOS 侧没有该
        模块。shim 保持调用约定不变（intltool-merge -x -u -c cache po <in> <out>，
        最后两个参数是 input/output），把 `_name="x"`/`_descr="x"` 之类的标记
        剥成 `name="x"`/`descr="x"`，即"无翻译"时的等价结果。
        """
        shim = os.path.join(self.build_folder, "tool-stubs", "bin", "intltool-merge")
        os.makedirs(os.path.dirname(shim), exist_ok=True)
        if not os.path.isfile(shim):
            save(self, shim, (
                "#!/usr/bin/env python3\n"
                '"""intltool-merge 替代：剥离 intltool 翻译标记（OHOS 无 XML::Parser）。"""\n'
                "import re\n"
                "import sys\n"
                "\n"
                "args = sys.argv[1:]\n"
                "if len(args) < 2:\n"
                "    sys.exit(1)\n"
                "src, dst = args[-2], args[-1]\n"
                "with open(src, encoding='utf-8') as handle:\n"
                "    content = handle.read()\n"
                "content = re.sub(r'(?<=\\s)_([A-Za-z][A-Za-z0-9_.-]*)\\s*=', r'\\1=', content)\n"
                "with open(dst, 'w', encoding='utf-8') as handle:\n"
                "    handle.write(content)\n"
            ))
            os.chmod(shim, 0o755)
            self.output.info(f"[libgda5] intltool-merge shim -> {shim}")
        return shim

    def _ensure_tool_stub(self, name):
        """生成一个仅满足 configure 存在性探测的构建工具 stub，返回其所在目录。"""
        stub_bin = os.path.join(self.build_folder, "tool-stubs", "bin")
        os.makedirs(stub_bin, exist_ok=True)
        stub = os.path.join(stub_bin, name)
        if not os.path.isfile(stub):
            save(self, stub, "#!/bin/sh\nexit 0\n")
            os.chmod(stub, 0o755)
            self.output.info(f"[libgda5] build-tool stub -> {stub}")
        return stub_bin

    def _glib_tool_bin(self):
        """返回 conan glib 包内含 glib-mkenums 的 bin 目录（不存在则 None）。"""
        dep = self.dependencies.get("glib")
        if dep is None or not dep.package_folder:
            return None
        for bindir in dep.cpp_info.bindirs:
            candidate = os.path.join(dep.package_folder, bindir)
            if os.path.exists(os.path.join(candidate, "glib-mkenums")):
                return candidate
        return None

    def _dep_include_dir(self, dep_name, header):
        """返回宿主依赖包内包含某个头文件的 include 目录（不存在则 None）。

        cpp_info.includedirs 之外，还要看包根的 include/（glib 的 proxy
        libintl.h 就打在这里，未列入 includedirs）。
        """
        dep = self.dependencies.get(dep_name)
        if dep is None or not dep.package_folder:
            return None
        candidates = [os.path.join(dep.package_folder, incdir)
                      for incdir in dep.cpp_info.includedirs]
        candidates.append(os.path.join(dep.package_folder, "include"))
        for candidate in candidates:
            if os.path.exists(os.path.join(candidate, header)):
                return candidate
        return None

    def _tool_binary(self, dep_name, exe_name):
        """返回 tool_requires 依赖包内可执行文件的绝对路径（不存在则 None）。"""
        dep = self.dependencies.build.get(dep_name)
        if dep is None or not dep.package_folder:
            return None
        for bindir in dep.cpp_info.bindirs:
            candidate = os.path.join(dep.package_folder, bindir, exe_name)
            if os.path.exists(candidate):
                return candidate
        return None
