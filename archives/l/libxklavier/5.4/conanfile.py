#!/usr/bin/env python3
"""Conan recipe — libxklavier 5.4 (autotools, HarmonyOS PC / aarch64).

libxklavier 是基于 XKB 的键盘配置库。OHOS 适配要点：

1. release tarball 缺 configure（Debian 的 pristine 上游包只有 configure.ac）
   → build() 里用 conan 工具链（autoconf/automake/libtool/gettext/pkgconf）
   执行 `autoreconf -fi` 自举；宿主 automake 损坏（@am_AUTOM4TE@ 未替换），
   故工具全部以 tool_requires 提供。
2. XKB 后端硬依赖 libxkbfile（`X11/extensions/XKBrules.h` 的 XkbRF_* API，
   xkl_xkb_init 在无 LIBXKBFILE_PRESENT 时直接 return -1）。libxkbfile 未
   发布到制品仓 → 配方内内嵌构建静态 libxkbfile.a（conandata.yml 的
   `xkbfile` 源），再通过 CFLAGS/LDFLAGS/PKG_CONFIG_PATH 暴露给 libxklavier
   configure/link，并把 libxkbfile.a 装进包内（静态消费者可链接）。
3. configure 需要 iso-codes.pc（纯数据包未发布）→ build() 生成最小 .pc；
   libxkbfile 的 configure 需要 kbproto.pc（xorgproto 合并了 kbproto）→
   生成指向 xorgproto 头文件的薄 .pc。
4. m4 宏裁剪：GOBJECT_INTROSPECTION_CHECK / VAPIGEN_CHECK / GTK_DOC_CHECK
   均无对应宏包 → build() 写 stub（定义 --disable-introspection /
   --disable-vala / --disable-gtk-doc 选项与 AM_CONDITIONAL）；doc/ 需要
   gtk-doc.make → 写空 stub 文件。
5. libxi 可选：configure 的 PKG_CHECK_MODULES(XINPUT, xi) 找不到时自动
   回退 have_xinput=no，XKB 后端不受影响（已裁剪）。
6. OHOS autotools 通用修复：生成的 configure 里 umask 077→022、
   shebang 改 /data/service/hnp/bin/bash（HMDFS/E002/E114）。

环境变量（ACLOCAL_PATH / PKG_CONFIG_PATH）必须在 generate() 里设置：
conan 的 buildenv 脚本在每次 self.run 结束后会把变量还原为 generate()
时刻的快照，若在 build() 里才设值，第二次 self.run 就丢了。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches, copy,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# ── OHOS autotools 通用修复 ─────────────────────────────────────────

def _prepare_autotools_env():
    """宿主损坏的 automake/aclocal 会硬编码不存在的 autoconf/autom4te 绝对
    路径；这里把它们指向 PATH 上实际存在的工具（conan tool_requires 提供）。"""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _patch_generated_configure(path):
    """E002/E114：OHOS/HMDFS 下 config.status 用 umask 077 建的临时目录不可写；
    /bin/sh 不存在 → shebang 改 bash 绝对路径。"""
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read()
    data = data.replace("umask 077", "umask 022")
    data = data.replace("#! /bin/sh", "#!/data/service/hnp/bin/bash")
    data = data.replace("#!/bin/sh", "#!/data/service/hnp/bin/bash")
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


# ── m4 / .pc stub 内容 ──────────────────────────────────────────────

_M4_GOBJECT_INTROSPECTION = """\
dnl Minimal GOBJECT_INTROSPECTION_CHECK stub — introspection 已裁剪 (--disable-introspection)
AC_DEFUN([GOBJECT_INTROSPECTION_CHECK],
[
  AC_ARG_ENABLE([introspection],
    [AS_HELP_STRING([--enable-introspection],
                    [Enable GObject introspection scanning (default: no)])],
    [enable_introspection=$enableval],
    [enable_introspection=no])
  AM_CONDITIONAL([HAVE_INTROSPECTION], [test "x$enable_introspection" = "xyes"])
  AC_SUBST([INTROSPECTION_MAKEFILE])
  AC_SUBST([INTROSPECTION_SCANNER])
  AC_SUBST([INTROSPECTION_COMPILER])
  AC_SUBST([INTROSPECTION_GENERATE])
  AC_SUBST([INTROSPECTION_GIRDIR])
  AC_SUBST([INTROSPECTION_TYPELIBDIR])
  AC_SUBST([INTROSPECTION_CFLAGS])
  AC_SUBST([INTROSPECTION_LIBS])
])
"""

_M4_VAPIGEN = """\
dnl Minimal VAPIGEN_CHECK stub — vala 绑定已裁剪 (--disable-vala)
AC_DEFUN([VAPIGEN_CHECK],
[
  AC_ARG_ENABLE([vala],
    [AS_HELP_STRING([--enable-vala],
                    [Enable Vala bindings (default: no)])],
    [enable_vala=$enableval],
    [enable_vala=no])
  AM_CONDITIONAL([ENABLE_VAPIGEN], [test "x$enable_vala" = "xyes"])
  AC_SUBST([VAPIGEN_MAKEFILE])
])
"""

_M4_GTK_DOC = """\
dnl Minimal GTK_DOC_CHECK stub — gtk-doc 文档已裁剪 (--disable-gtk-doc)
AC_DEFUN([GTK_DOC_CHECK],
[
  AC_ARG_ENABLE([gtk-doc],
    [AS_HELP_STRING([--enable-gtk-doc],
                    [Use gtk-doc to build documentation (default: no)])],
    [enable_gtk_doc=$enableval],
    [enable_gtk_doc=no])
  AM_CONDITIONAL([ENABLE_GTK_DOC], [test "x$enable_gtk_doc" = "xyes"])
  AM_CONDITIONAL([GTK_DOC_USE_LIBTOOL], [test "x$enable_gtk_doc" = "xyes"])
  AC_SUBST([GTK_DOC_USE_LIBTOOL])
])
"""

_ISO_CODES_PC = """\
prefix=/usr/share/iso-codes
datarootdir=${prefix}

Name: iso-codes
Description: ISO country, language, script codes and their translations
Version: 4.16.0
"""


class LibxklavierConan(ConanFile):
    name = "libxklavier"
    version = "5.4"
    description = "XKB 键盘配置库，为 X11 键盘布局管理提供 API"
    license = "LGPL-2.1+"
    homepage = "https://gitlab.freedesktop.org/archived/libxklavier"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # 生成 x11.pc / glib-2.0.pc / gobject-2.0.pc / libxml-2.0.pc
    # （PkgConfigDeps 输出到 generators 目录，AutotoolsToolchain 自动把
    # 该目录 prepend 进 PKG_CONFIG_PATH）。
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 已确认发布到 ohpcd（conan download 验证）：
        # libx11/1.8.13、glib/2.88.0.1、libxml2/2.15.3.1。
        # libxkbfile 未发布 → 配方内内嵌静态构建（见 build()）。
        # 公共头 xklavier.h #include <X11/Xlib.h> 与 <glib-object.h> →
        # libx11/glib 必须 transitive_headers=True，否则 CMakeDeps 消费者
        # 拿不到它们的 include 目录（test_package 编译即失败）。
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("glib/2.88.0.1", transitive_headers=True)
        self.requires("libxml2/2.15.3.1")
        # xorgproto（kbproto 已并入）为纯头文件包：libxkbfile 编译需要其
        # X11/extensions/XKBgeom.h 等头。声明为直接私有依赖，其 package_folder
        # 才在 self.dependencies 里可用（作为传递依赖时 package_folder=None）。
        # transitive_headers=True：与 libice/libsm 同法，消费方也能拿到头文件；
        # 且被 libx11 以同样方式 require → 图合并后该依赖为 visible，必须在
        # package_info().cpp_info.requires 里引用（Conan 2.29 校验）。
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def build_requirements(self):
        # 宿主 automake 损坏（@am_AUTOM4TE@ 未替换）+ 无 autopoint/
        # libtoolize/gettextize/msgfmt → 全部用 conan 工具链包。
        # tool_requires 用 build profile 解析（-pr:h 与 -pr:b 同 profile）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("gettext/0.22.5.1")
        self.tool_requires("pkgconf/3.0.5")

    def validate(self):
        # R32: settings.os 必须 in ("Linux", "OHOS")，不能 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxklavier is supported only on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── 路径辅助 ────────────────────────────────────────────────────

    def _xkbfile_prefix(self):
        return os.path.join(self.build_folder, "xkbfile-prefix")

    def _pc_stubs_dir(self):
        return os.path.join(self.build_folder, "pc-stubs")

    def _m4_stubs_dir(self):
        return os.path.join(self.source_folder, "m4-ohos")

    def _dep_folder(self, name):
        """按名字找依赖包文件夹（含 host 与 build 上下文、直接与传递依赖）。
        注意：header-only 的传递依赖 package_folder 为 None，需声明为直接
        依赖（见 requirements() 里 xorgproto 的注释）。"""
        for dep in self.dependencies.values():
            try:
                if dep.ref.name == name and getattr(dep, "package_folder", None):
                    return dep.package_folder
            except Exception:
                continue
        return None

    def _tool_aclocal_dirs(self):
        """tool_requires 包里的 share/aclocal（gettext/libtool/pkgconf 宏）。"""
        dirs = []
        for pkg in ("pkgconf", "gettext", "libtool"):
            folder = self._dep_folder(pkg)
            if folder:
                acl = os.path.join(folder, "share", "aclocal")
                if os.path.isdir(acl):
                    dirs.append(acl)
        return dirs

    def _fix_la_dir(self, lib_dir):
        """清洗单个 lib/ 目录下所有 .la 文件的失效路径（幂等，详见
        _fix_dep_la_files 的 docstring）。"""
        import re
        if not lib_dir or not os.path.isdir(lib_dir):
            return
        for entry in sorted(os.listdir(lib_dir)):
            if not entry.endswith(".la"):
                continue
            la_path = os.path.join(lib_dir, entry)
            with open(la_path, "r", encoding="utf-8", errors="ignore") as handle:
                content = handle.read()
            new_content = content
            # 1. libdir 指向的目录若不存在（构建期临时目录已清理/迁移），
            #    改写到 .la 实际所在目录，避免 libtool 按 libdir/name 找 .la
            new_content = re.sub(
                r"(?m)^libdir=.*$",
                "libdir='{0}'".format(lib_dir),
                new_content)
            # 2. 去掉指向不存在 .la 的引用（注意路径可能紧跟行尾引号，排除
            #    引号与空白字符，避免把结尾 ' 一起吞掉破坏引号配对）
            for match in re.finditer(r"([^\s'\"]+\.la)", new_content):
                la_ref = match.group(1)
                if la_ref and not os.path.isfile(la_ref):
                    new_content = new_content.replace(la_ref, "")
            # 3. 去掉指向不存在目录的 -L
            for match in re.finditer(r"-L([^\s'\"]+)", new_content):
                ldir = match.group(1)
                if ldir and not os.path.isdir(ldir):
                    new_content = new_content.replace(match.group(0), "")
            new_content = re.sub(r"  +", " ", new_content)
            if new_content != content:
                with open(la_path, "w", encoding="utf-8") as handle:
                    handle.write(new_content)

    def _fix_dep_la_files(self):
        """libtool .la 在依赖包文件夹里记录了构建期绝对路径（conan create 后
        已清理，或从旧的 CONAN_HOME=~/.cache/conan2 迁移过来）→ 链接时
        "is not a valid libtool archive"（libtool 按 libdir 找依赖 .la）。
        处理三处：
          1. libdir= 指回 .la 文件实际所在目录（依赖包 lib/）
          2. dependency_libs 里指向不存在 .la 的引用去掉
          3. dependency_libs 里指向不存在目录的 -L 去掉
        与 libx11 配方同法，跨包通用，幂等。"""
        for dep in self.dependencies.values():
            try:
                dep_lib = os.path.join(dep.package_folder, "lib")
            except Exception:
                continue
            self._fix_la_dir(dep_lib)

    def _fix_tool_perl_shebangs(self):
        """automake 的 .aclocal-real/.automake-real shebang 指向宿主 perl
        （/data/service/hnp/bin/perl 5.42.0），而 conanbuildenv 的 PERL5LIB 是
        conan perl（5.42.2）的模块 → 宿主 perl 加载 conan 的 XS 模块 ABI 不匹配
        （'Perl_my_cxt_init: symbol not found'）。把 shebang 改成 conan perl
        （与 .autom4te-real 的既有做法一致）。幂等。"""
        perl = None
        auto_bin = None
        for dep in self.dependencies.values():
            try:
                if dep.ref.name == "perl" and getattr(dep, "package_folder", None):
                    perl = os.path.join(dep.package_folder, "bin", "perl")
                elif dep.ref.name == "automake" and getattr(dep, "package_folder", None):
                    auto_bin = os.path.join(dep.package_folder, "bin")
            except Exception:
                continue
        if not perl or not os.path.isfile(perl):
            self.output.warning("conan perl 未找到，跳过 automake shebang 修复")
            return
        if not auto_bin or not os.path.isdir(auto_bin):
            return
        for name in (".aclocal-real", ".aclocal-1.18-real",
                     ".automake-real", ".automake-1.18-real"):
            script = os.path.join(auto_bin, name)
            if not os.path.isfile(script):
                continue
            with open(script, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            new_content = content
            for old_shebang in ("#!/data/service/hnp/bin/perl",
                                "#!/bin/perl", "#!/usr/bin/perl"):
                new_content = new_content.replace(old_shebang, f"#!{perl}")
            if new_content != content:
                with open(script, "w", encoding="utf-8") as f:
                    f.write(new_content)
                self.output.info(f"已修复 {name} shebang → {perl}")

    # ── generate ────────────────────────────────────────────────────

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        # config.guess 无法识别 HarmonyOS（E007）：显式给 triplet，跳过探测。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # 可选特性裁剪（对应 m4 stub 定义的选项）
        tc.configure_args.append("--disable-introspection")
        tc.configure_args.append("--disable-vala")
        tc.configure_args.append("--disable-gtk-doc")
        tc.configure_args.append("--with-xkb-base=/usr/share/X11/xkb")

        # libxklavier configure 的 AC_CHECK_HEADER(X11/extensions/XKBrules.h)
        # 用裸 CPPFLAGS 编译探测（不读 pkg-config 结果）→ 必须显式加 include；
        # 同时让 AM_GNU_GETTEXT 的 libintl.h 探测命中 glib 包内的 proxy libintl。
        inc_dirs = []
        for dep in ("libx11", "glib", "xorgproto"):
            folder = self._dep_folder(dep)
            if folder:
                inc_dirs.append(os.path.join(folder, "include"))
        # libxkbfile 的安装前缀（build() 内先构建），configure 探测 XKBrules.h
        # 需要它的 include，链接需要它的 lib。
        inc_dirs.append(os.path.join(self._xkbfile_prefix(), "include"))
        tc.extra_cflags.extend([f"-I{d}" for d in inc_dirs])
        tc.extra_ldflags.append(f"-L{os.path.join(self._xkbfile_prefix(), 'lib')}")
        glib_folder = self._dep_folder("glib")
        if glib_folder:
            tc.extra_ldflags.append(f"-L{os.path.join(glib_folder, 'lib')}")

        # ⚠️ ACLOCAL_PATH / PKG_CONFIG_PATH 必须在 generate() 里设（见模块 docstring）：
        # conan 的 buildenv 在每次 self.run 后把变量还原为 generate() 时刻的快照。
        aclocal_paths = [self._m4_stubs_dir()] + self._tool_aclocal_dirs()
        old_acl = os.environ.get("ACLOCAL_PATH", "")
        if old_acl:
            aclocal_paths.append(old_acl)
        os.environ["ACLOCAL_PATH"] = os.pathsep.join(aclocal_paths)

        pkg_config_paths = [
            os.path.join(self._xkbfile_prefix(), "lib", "pkgconfig"),
            self._pc_stubs_dir(),
        ]
        old_pc = os.environ.get("PKG_CONFIG_PATH", "")
        if old_pc:
            pkg_config_paths.append(old_pc)
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(pkg_config_paths)

        # autopoint：gettext 包把 prefix 烤成 "/"（datarootdir=//share），
        # autoreconf 的 autopoint 步骤需要 gettext_datadir 环境变量指到真实
        # 数据目录（archive.dir.tar.xz）。该变量不被 conan 的 buildenv 追踪，
        # 设置一次即可跨 self.run 保留。
        gettext_folder = self._dep_folder("gettext")
        if gettext_folder:
            os.environ["gettext_datadir"] = os.path.join(
                gettext_folder, "share", "gettext")

        # glib 工具（glib-genmarshal/glib-mkenums）：libxklavier Makefile 里
        # glib-mkenums 用裸名调用 → 需要 glib 的 bin/ 在 PATH 上
        glib_folder = self._dep_folder("glib")
        if glib_folder:
            glib_bin = os.path.join(glib_folder, "bin")
            old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = os.pathsep.join(
                [glib_bin] + ([old_path] if old_path else []))

        tc.generate()
        self._patch_glib_pc()

    def _patch_glib_pc(self):
        """PkgConfigDeps 生成的 glib-2.0.pc 缺 glib_genmarshal 等变量；
        libxklavier Makefile.am 用 `pkg-config --variable=glib_genmarshal
        glib-2.0` 拿工具绝对路径 → 补上（bindir 已在 pc 里定义）。"""
        glib_folder = self._dep_folder("glib")
        if not glib_folder:
            return
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc, "r", encoding="utf-8") as f:
            content = f.read()
        if "glib_genmarshal" not in content:
            content += (
                "\nglib_genmarshal=${bindir}/glib-genmarshal\n"
                "glib_mkenums=${bindir}/glib-mkenums\n"
                "glib_compile_resources=${bindir}/glib-compile-resources\n"
                "glib_compile_schemas=${bindir}/glib-compile-schemas\n"
            )
            with open(glib_pc, "w", encoding="utf-8") as f:
                f.write(content)

    # ── build ───────────────────────────────────────────────────────

    def _write_m4_stubs(self):
        stub_dir = self._m4_stubs_dir()
        os.makedirs(stub_dir, exist_ok=True)
        for fname, content in (
                ("gobject-introspection.m4", _M4_GOBJECT_INTROSPECTION),
                ("vala.m4", _M4_VAPIGEN),
                ("gtk-doc.m4", _M4_GTK_DOC)):
            path = os.path.join(stub_dir, fname)
            if not os.path.isfile(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
        # doc/reference/Makefile.am 里 `include $(top_srcdir)/gtk-doc.make`，
        # 且其 `EXTRA_DIST +=` 需要先有 `EXTRA_DIST =` 初始化（否则 automake 报
        # "EXTRA_DIST must be set with '=' before using '+='")
        gtkdoc_make = os.path.join(self.source_folder, "gtk-doc.make")
        if not os.path.isfile(gtkdoc_make):
            with open(gtkdoc_make, "w", encoding="utf-8") as f:
                f.write("# Minimal gtk-doc.make stub (docs disabled)\n"
                        "EXTRA_DIST =\n"
                        "CLEANFILES =\n")

    def _write_pc_stubs(self):
        pc_dir = self._pc_stubs_dir()
        os.makedirs(pc_dir, exist_ok=True)
        iso_codes = os.path.join(pc_dir, "iso-codes.pc")
        if not os.path.isfile(iso_codes):
            with open(iso_codes, "w", encoding="utf-8") as f:
                f.write(_ISO_CODES_PC)
        # kbproto 已并入 xorgproto（未单独发布）→ 薄 .pc 指向 xorgproto include
        xorgproto = self._dep_folder("xorgproto")
        kbproto = os.path.join(pc_dir, "kbproto.pc")
        if xorgproto and not os.path.isfile(kbproto):
            with open(kbproto, "w", encoding="utf-8") as f:
                f.write(
                    "prefix={prefix}\n"
                    "includedir=${{prefix}}/include\n"
                    "\n"
                    "Name: kbproto\n"
                    "Description: X.Org XKB protocol headers\n"
                    "Version: 1.0.7\n"
                    "Cflags: -I\"${{includedir}}\"\n".format(prefix=xorgproto))
        elif not xorgproto:
            self.output.warning("xorgproto 包文件夹未找到，kbproto.pc 未生成")
        return pc_dir

    def _build_xkbfile(self):
        """内嵌构建静态 libxkbfile.a（未发布依赖）到 build_folder/xkbfile-prefix。"""
        src = os.path.join(self.source_folder, "xkbfile")
        prefix = self._xkbfile_prefix()
        if not os.path.isdir(os.path.join(src, "configure")):
            get(self, url=self.conan_data["xkbfile"]["url"],
                sha256=self.conan_data["xkbfile"]["sha256"],
                destination=src, strip_root=True)
        # E114/HMDFS：xkbfile tarball 自带的 configure 里有 umask 077 + mktemp
        # 的 config.status 临时目录创建逻辑（生成在 0700 下不可写）→ 先修掉
        _patch_generated_configure(os.path.join(src, "configure"))
        os.makedirs(prefix, exist_ok=True)
        self.output.info(f"内嵌构建 libxkbfile → {prefix}")
        cfg = (
            f'cd "{src}" && ./configure '
            f'--prefix="{prefix}" '
            f'--build=aarch64-unknown-linux-gnu '
            f'--host=aarch64-unknown-linux-gnu '
            f'--disable-shared --enable-static '
            f'CFLAGS="$CFLAGS -fPIC"'
        )
        self.run(cfg, env="conanbuild")
        self.run(f'cd "{src}" && make -j1', env="conanbuild")
        self.run(f'cd "{src}" && make install', env="conanbuild")

    def _write_gtkdocize_stub(self):
        """autoreconf 检测到 configure.ac 用 GTK_DOC_CHECK（我们的 stub）就会去
        找 `gtkdocize` 工具拷贝 gtk-doc 基础设施；gtk-doc 未发布 → 放一个
        空操作 stub（gtk-doc.make 与 gtk-doc.m4 已由本配方提供，无需拷贝）。"""
        bin_dir = os.path.join(self.build_folder, "ohos-bin")
        os.makedirs(bin_dir, exist_ok=True)
        stub = os.path.join(bin_dir, "gtkdocize")
        if not os.path.isfile(stub):
            with open(stub, "w", encoding="utf-8") as f:
                f.write("#!/data/service/hnp/bin/bash\nexit 0\n")
            os.chmod(stub, 0o755)
        return bin_dir

    def build(self):
        apply_conandata_patches(self)
        _prepare_autotools_env()

        # 0) 清理依赖包 .la 里的失效绝对路径引用（libtool 链接必需），
        #    并把 automake perl 脚本 shebang 修到 conan perl（autoreconf 必需）
        self._fix_dep_la_files()
        self._fix_tool_perl_shebangs()

        # 1) pc/m4 stub 先生成（目录路径在 generate() 已写进
        #    PKG_CONFIG_PATH/ACLOCAL_PATH，这里只需落盘文件）
        self._write_pc_stubs()
        self._write_m4_stubs()
        gtkdocize_dir = self._write_gtkdocize_stub()

        # 2) 内嵌 libxkbfile 静态构建（必须先于 libxklavier configure）
        self._build_xkbfile()
        #    其生成/复用 libxkbfile.la 的 dependency_libs 可能仍带失效路径
        #    （若 build 目录被 conan 复用，旧 .la 不会自动重链）→ 清洗
        self._fix_la_dir(os.path.join(self._xkbfile_prefix(), "lib"))

        # 3) autoreconf 自举（release 包缺 configure）。
        # 必须用 $AUTORECONF（conan 工具链，conanbuild env 已把 AUTOCONF/
        # AUTOMAKE/ACLOCAL/LIBTOOLIZE/AUTOM4TE 指到 conan 工具），而不是裸
        # `autoreconf`——后者会命中宿主 /data/service/hnp/bin 下损坏的版本
        # （Perl 模块链与 conan perl 不兼容，BEGIN failed）。
        # PATH 里带上 gtkdocize stub 目录。
        self.run(f'PATH="$PATH:{gtkdocize_dir}" "$AUTORECONF" -fi',
                 cwd=self.source_folder, env="conanbuild")

        # 4) OHOS 通用修复（必须等 autoreconf 生成 configure 之后再改）
        _patch_generated_configure(os.path.join(self.source_folder, "configure"))

        # 5) configure + make
        autotools = Autotools(self)
        autotools.configure()
        # E074: OHOS 下并行 make 的 jobserver fifo 会 EPERM → -j1
        # Makefile 里 glib-mkenums 用裸名调用，会命中宿主 /data/service/hnp/bin
        # 下 shebang 损坏（/usr/bin/perl 不存在）的版本 → PATH 前置 conan glib bin
        glib_folder = self._dep_folder("glib")
        glib_bin = os.path.join(glib_folder, "bin") if glib_folder else ""
        self.run(f'PATH="{glib_bin}:$PATH" make -j1', env="conanbuild")
        # 上游 make check（test_config/test_monitor）需要 X server
        # （XOpenDisplay），OHOS 无 X → 不跑，详见 test_package/MANIFEST.yml。

    # ── package ─────────────────────────────────────────────────────

    def package(self):
        # make install（PATH 前置 conan glib bin，同 build() 的裸名工具问题）
        glib_folder = self._dep_folder("glib")
        glib_bin = os.path.join(glib_folder, "bin") if glib_folder else ""
        self.run(f'PATH="{glib_bin}:$PATH" make install '
                 f'DESTDIR="{self.package_folder}"', env="conanbuild")
        # 把内嵌的静态 libxkbfile.a 一起装进包：静态 libxklavier.a 的消费者
        # 需要它解析 XkbRF_* 符号。
        xkbfile_lib = os.path.join(self._xkbfile_prefix(), "lib")
        if os.path.isfile(os.path.join(xkbfile_lib, "libxkbfile.a")):
            copy(self, "libxkbfile.a", src=xkbfile_lib,
                 dst=os.path.join(self.package_folder, "lib"))
        # 清理 libtool .la（记录的是构建期绝对路径，不可迁移）
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "**", "*.la"),
                              recursive=True):
            try:
                os.remove(_la)
            except OSError:
                pass

    # ── package_info ────────────────────────────────────────────────

    def package_info(self):
        self.cpp_info.libs = ["xklavier", "xkbfile"]
        self.cpp_info.includedirs = ["include", "include/libxklavier"]
        # 静态交付：消费方编译/链接需要 libx11/glib/gobject/libxml2 的头文件
        # 与静态库（CMakeDeps/PkgConfigDeps 按依赖图传递）。
        self.cpp_info.requires = [
            "libx11::libx11",
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "libxml2::libxml2",
            "xorgproto::xorgproto",
        ]
        self.cpp_info.system_libs = ["m", "pthread", "dl", "rt"]
        self.cpp_info.set_property("pkg_config_name", "libxklavier")
        self.cpp_info.set_property("cmake_file_name", "libxklavier")
        self.cpp_info.set_property("cmake_target_name", "libxklavier::libxklavier")
