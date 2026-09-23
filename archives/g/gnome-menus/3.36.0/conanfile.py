#!/usr/bin/env python3
"""Conan recipe — gnome-menus 3.36.0 (libgnome-menu-3.0 + GMenu introspection)。

alacarte 的上游依赖 libgnome-menu-3.0（提供 GMenu typelib，供 pygobject 的
`from gi.repository import GMenu` 使用）。gnome-menus 是 C 库（autotools），
构建时经 GOBJECT_INTROSPECTION_CHECK 生成 GMenu-3.0.gir + GMenu-3.0.typelib。

依赖（本团队发布的正式包，无 scratch 路径）：
  - glib/2.84.0.1（共享，提供 gio-unix-2.0；typelib 运行时需 dlopen .so）
  - gobject-introspection/1.78.1.1（开启 introspection，提供 g-ir-scanner/
    g-ir-compiler 工具链 + GLib/GObject/Gio typelib，生成 GMenu typelib 用）
  - libintl/0.26.1（合并 libintl.so.8：libintl_* + g_libintl_*，g-ir-scanner
    进程内 python 与共享 glib 共存的关键）

注意（本环境特有，配方内可复现）：
  - g-ir-scanner 用 distutils 调 `cc`，需 CC=/data/service/hnp/bin/clang；
    调 `ldd`，环境无 —— gobject-introspection 配方已在构建环境生成 ldd shim
  - 合并 libintl 置于 LD_LIBRARY_PATH 首位（由 libintl/0.26.1 提供）
"""
import glob
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

HNP_BIN = "/data/service/hnp/bin"

# Python 3.12 已移除 distutils，而 g-ir-scanner 的 giscanner/utils.py、
# giscanner/ccompiler.py 在模块级 `import distutils`（CI #42069 消费本包的
# GISCAN 步骤即报 ModuleNotFoundError）。本机系统 python 与 conan python 都不带
# distutils/setuptools，故随配方自带 gi-distutils/（setuptools 的 distutils
# 兼容层，与 gobject-introspection/1.78.1.1 配方同源），由 g-ir wrapper 注入
# PYTHONPATH。仅这三个顶层包为运行期必需（distutils 依赖 jaraco.functools，
# jaraco.functools 依赖 more_itertools）。
_VENDORED_TOP_LEVEL = ("distutils", "jaraco", "more_itertools")


class GnomeMenusConan(ConanFile):
    name = "gnome-menus"
    version = "3.36.0"
    description = "Implementation of the freedesktop.org menu specification"
    license = "LGPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gnome-menus"
    url = "https://gitlab.gnome.org/GNOME/gnome-menus"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        # 共享 glib：typelib 运行时需 dlopen libglib-2.0.so.0 等
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # 正式 infra：g-ir 工具链 + typelib（gobject-introspection/1.78.1.1）
        self.requires("gobject-introspection/1.78.1.1", transitive_libs=True)
        # 合并 libintl（libintl_* + g_libintl_*）
        self.requires("libintl/0.26.1", transitive_libs=True)

    def export_sources(self):
        export_conandata_patches(self)
        # distutils 兼容层需随 export 一起进入构建上下文（generate()/build() 使用）
        _gi_src = os.path.join(self.recipe_folder, "gi-distutils")
        if os.path.isdir(_gi_src):
            copy(self, "*", _gi_src,
                 os.path.join(self.export_sources_folder, "gi-distutils"))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _pkg_dir(self, prefix, rel):
        """按依赖 ref 前缀找 package_folder 下路径（含 glob 兜底）。"""
        for _dep in self.dependencies.values():
            if _dep.package_folder and str(_dep.ref).startswith(prefix):
                _p = os.path.join(_dep.package_folder, rel)
                if os.path.exists(_p):
                    return _p
        _cands = glob.glob("/storage/Users/currentUser/.conan2/p/%s*/p" % prefix.split("/")[0])
        for _c in _cands:
            _p = os.path.join(_c, rel)
            if os.path.exists(_p):
                return _p
        return None

    def _sanitize_build_flags(self):
        """剥离 worker 注入的 HNP 默认前缀（~/usr/local）编译/链接标志。

        CI worker 的 shell 预先导出了指向 HNP 默认前缀的 flags，例如
        CFLAGS=-I$HOME/usr/local/include、LDFLAGS=-L$HOME/usr/local/lib。
        该前缀下可能残留旧版 glib（静态 libgio-2.0.a / libglib-2.0.a），一旦透传：
          · configure 把它写进 Makefile 的 LDFLAGS，libtool 再记入
            libgnome-menu-3.la 的 dependency_libs；
          · g-ir-scanner 展开 .la 并拼接自身 CFLAGS/LDFLAGS
            （giscanner/dumper.py:226/256、ccompiler.py:70-79）→ 链接器优先命中
            ~/usr/local/lib/libgio-2.0.a，报
              ld.lld: error: undefined symbol: g_libintl_gettext
              ld.lld: error: undefined symbol: pcre2_config_8
        这里只做"减法"：剔除引用该前缀的 token，保留其余（toolchain 的 -DNDEBUG、
        -O3 等）不动，也不额外注入任何库（曾试探性加 -lintl，会使 configure 的
        conftest 在无 scanner wrapper LD_LIBRARY_PATH 时加载不到 libintl.so.8）。
        """
        prefixes = [os.path.expanduser("~/usr/local"), "/usr/local"]
        env_prefix = os.environ.get("DEFAULT_PREFIX")
        if env_prefix:
            prefixes.append(env_prefix)
        stripped = {}
        for var in ("CPPFLAGS", "CFLAGS", "LDFLAGS"):
            raw = os.environ.get(var, "")
            if not raw:
                continue
            kept = [tok for tok in shlex.split(raw)
                    if not any(p in tok for p in prefixes)]
            new = " ".join(kept)
            if new != raw:
                os.environ[var] = new
                stripped[var] = raw
        return stripped

    def _vendored_distutils_dir(self):
        """随配方自带的 distutils 兼容层目录（gi-distutils/）。"""
        for _base in (self.source_folder, self.export_sources_folder,
                      self.recipe_folder):
            _d = os.path.join(_base, "gi-distutils")
            if os.path.isdir(os.path.join(_d, "distutils")):
                return _d
        return None

    def _install_vendored_distutils(self, dst):
        """把 gi-distutils/ 的必需顶层包复制到 dst（幂等），供 g-ir wrapper
        的 PYTHONPATH 使用。返回 distutils 是否就位。"""
        if os.path.isdir(os.path.join(dst, "distutils")):
            return True
        _src = self._vendored_distutils_dir()
        if not _src:
            return False
        for _mod in _VENDORED_TOP_LEVEL:
            _s = os.path.join(_src, _mod)
            if not os.path.exists(_s):
                continue
            if os.path.isdir(_s):
                shutil.copytree(_s, os.path.join(dst, _mod), dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__",
                                                              "*.pyc"))
            else:
                shutil.copy2(_s, os.path.join(dst, _mod))
        return os.path.isdir(os.path.join(dst, "distutils"))

    def _python_runtime(self):
        """解析 conan python 运行时（python/3.12.9，经 gobject-introspection 传递）。

        返回 (package_folder, bin_dir, lib_dir, lib_dynload_dir)；未找到时各项为 ''。
        _giscanner 扩展后缀与运行 scanner 的 python 必须一致，故不能依赖 PATH 上
        的系统 python。
        """
        _pkg = ""
        for _dep in self.dependencies.values():
            if _dep.package_folder and str(_dep.ref).startswith("python/"):
                _pkg = _dep.package_folder
                break
        if not _pkg:
            return "", "", "", ""
        _bin = os.path.join(_pkg, "bin")
        _lib = os.path.join(_pkg, "lib")
        _dynload = ""
        for _d in sorted(glob.glob(os.path.join(_lib, "python3.*"))):
            if os.path.isdir(os.path.join(_d, "lib-dynload")):
                _dynload = os.path.join(_d, "lib-dynload")
                break
        return _pkg, _bin, _lib, _dynload

    def _install_giscanner_for_scan(self, src, dst):
        """把 gobject-introspection 包内的 giscanner（含 _giscanner.so）复制到
        conan python 的 lib-dynload 并补签 .so，使 GISCAN 可 dlopen。

        E212：鸿蒙 loader 白名单按进程绑定，conan python 只能 dlopen 自身安装树
        lib-dynload 下的扩展（gobject-introspection 包 p/ 路径下的 _giscanner.so
        不可加载，CI #37178/#37213 证实）；构建目录 b/ 同样不可加载。
        """
        if not os.path.isdir(src):
            self.output.warning("gnome-menus: giscanner dir not found: %s" % src)
            return False
        shutil.copytree(src, dst, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for _so in glob.glob(os.path.join(dst, "**", "*.so"), recursive=True):
            self._sign_elf(_so)
        self.output.info("gnome-menus: giscanner installed to %s" % dst)
        return True

    def _sign_elf(self, path):
        """E077：ELF 自签名（原子方式，非 ELF 跳过）。"""
        try:
            with open(path, "rb") as _f:
                if _f.read(4) != b"\x7fELF":
                    return
        except OSError:
            return
        _objcopy = os.path.join(HNP_BIN, "llvm-objcopy")
        _signer = os.path.join(HNP_BIN, "binary-sign-tool")
        if not (os.path.isfile(_objcopy) and os.path.isfile(_signer)):
            self.output.warning("gnome-menus: signing tools unavailable, skip %s" % path)
            return
        _mode = os.stat(path).st_mode
        _tmp = "%s.signing" % path
        try:
            shutil.copy2(path, _tmp)
            self.run(f'"{_objcopy}" --remove-section .codesign "{_tmp}" || true')
            self.run(f'"{_signer}" sign -inFile "{_tmp}" -outFile "{_tmp}" -selfSign 1')
            os.chmod(_tmp, _mode)
            os.replace(_tmp, path)
        finally:
            if os.path.exists(_tmp):
                os.remove(_tmp)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--enable-introspection=yes"])
        tc.generate()
        # glib package_info 未声明 gio-unix-2.0 组件 → PkgConfigDeps 不生成其 .pc。
        # 复制 glib 全部 .pc 进 generators 目录，使 gio-unix-2.0 可解析（同 pygobject）。
        glib_pc = self._pkg_dir("glib/", "lib/pkgconfig")
        if glib_pc:
            for _f in sorted(os.listdir(glib_pc)):
                if _f.endswith(".pc"):
                    _d = os.path.join(self.generators_folder, _f)
                    if not os.path.exists(_d):
                        shutil.copy2(os.path.join(glib_pc, _f), _d)

        gir_pkg = self._pkg_dir("gobject-introspection/", "") or ""
        intl_lib = self._pkg_dir("libintl/", "lib") or ""
        glib_lib = self._pkg_dir("glib/", "lib") or ""
        gir_dir = os.path.join(gir_pkg, "share", "gir-1.0")

        # 配方内生成 g-ir wrapper：设置 LD_LIBRARY_PATH（合并 libintl 首位 + glib
        # libdir）+ --includedir（含 Gio-2.0.gir 等），再 exec 正式包的工具。
        # 构建 env 的 LD_LIBRARY_PATH 不传播到 make 子进程，故 wrapper 自持。
        wrapper_dir = os.path.join(self.build_folder, "gi-wrappers")
        os.makedirs(wrapper_dir, exist_ok=True)
        # distutils 兼容层放在 wrapper 旁，由 wrapper 注入 PYTHONPATH：g-ir-scanner
        # 的 giscanner/utils.py:385 `import distutils.cygwinccompiler`（Python 3.12
        # 无 stdlib distutils，CI #42069 的 GISCAN 失败根因）。
        _vendored_dir = os.path.join(wrapper_dir, "gi-distutils")
        if self._install_vendored_distutils(_vendored_dir):
            self.output.info("gnome-menus: vendored distutils -> %s" % _vendored_dir)
        else:
            self.output.warning("gnome-menus: gi-distutils/ not found; "
                                "g-ir-scanner may fail: No module named 'distutils'")
        # ldd shim：g-ir-scanner 的 giscanner/shlibs.py 用 ldd 解析 --library 对应
        # 的 soname，而鸿蒙 PC 无 ldd（hnp/usr/system bin 均无）。
        _ldd_shim = os.path.join(wrapper_dir, "ldd")
        with open(_ldd_shim, "w") as f:
            f.write("#!/bin/sh\n")
            f.write("for f in \"$@\"; do\n")
            f.write("  %s/llvm-readelf -d \"$f\" 2>/dev/null | grep -E 'Shared library' | sed -E 's/.*\\[(.*)\\]/\\t\\1 => \\1/'\n" % HNP_BIN)
            f.write("done\n")
        os.chmod(_ldd_shim, 0o755)

        # g-ir-scanner 是 Python 脚本 + `giscanner._giscanner` C 扩展，扩展的
        # EXT_SUFFIX 必须与运行它的 python 一致，且鸿蒙 loader 只允许 conan python
        # dlopen 自身安装树 lib-dynload 下的扩展（E212，#37178/#37213：b/ 与其他包
        # p/ 均不可加载）→ 显式用 conan python 运行，并把 giscanner（含已签名
        # _giscanner.so）复制进它的 lib-dynload。
        py_pkg, py_bin, py_lib, py_dynload = self._python_runtime()
        if py_dynload and gir_pkg:
            self._install_giscanner_for_scan(
                os.path.join(gir_pkg, "lib", "gobject-introspection", "giscanner"),
                os.path.join(py_dynload, "giscanner"))

        _env = ("export LD_LIBRARY_PATH='%s:%s:%s:$LD_LIBRARY_PATH'\n"
                "export CC='%s/clang'\n"
                "export PKG_CONFIG_PATH=\"%s\"\n"
                % (intl_lib, glib_lib, py_lib, HNP_BIN, self.generators_folder))
        # CI worker 的环境 CFLAGS/CPPFLAGS/LDFLAGS 指向 HNP 默认前缀 ~/usr/local
        # （其中可能残留旧版 glib 的静态库）。AutotoolsToolchain 会原样透传这些
        # 环境变量（conanautotoolstoolchain.sh 的 ${CPPFLAGS:-}），于是：
        #   ① 主库链接被 -L~/usr/local/lib 污染，libtool 把该路径写进
        #      libgnome-menu-3.la 的 dependency_libs；
        #   ② g-ir-scanner 探针程序展开 .la + 自身拼接 CFLAGS/LDFLAGS
        #      （giscanner/dumper.py:226/256、ccompiler.py:70-79）→ 优先命中
        #      ~/usr/local/lib/libgio-2.0.a（旧 glib 静态库），报
        #        ld.lld: error: undefined symbol: g_libintl_gettext
        #        >>> referenced by ... in archive ~/usr/local/lib/libgio-2.0.a
        #        （或旧静态 glib 缺 pcre2 时的 pcre2_* undefined）。
        # 这三处污染在 build() 入口由 _sanitize_build_flags() 剥离（只做减法，
        # 保留 toolchain 的 -DNDEBUG/-O3 等），wrapper 不再自行导出，直接继承
        # 剥离后的进程环境。
        if py_pkg:
            # PYTHONHOME/PATH 指向 conan python：scanner 子进程的 python 版本与
            # _giscanner 扩展后缀必须一致（系统 python 后缀为 .cpython-312.so，
            # 与包内扩展名不匹配 → ModuleNotFoundError: giscanner._giscanner）。
            _env += ("export PYTHONHOME='%s'\n"
                     "export PATH=\"%s:%s:$PATH\"\n"
                     % (py_pkg, py_bin, wrapper_dir))
        else:
            self.output.warning("gnome-menus: conan python not found in graph; "
                                "falling back to PATH python3 for g-ir-scanner")
            _env += "export PATH=\"%s:$PATH\"\n" % wrapper_dir
        # PYTHONPATH 首位必须是 python lib-dynload（内含 giscanner + 扩展），
        # 其次是随配方自带的 distutils 兼容层（giscanner/utils.py 模块级 import）。
        _py_path = ":".join(p for p in (py_dynload, _vendored_dir) if p)
        _env += "export PYTHONPATH=\"%s${PYTHONPATH:+:$PYTHONPATH}\"\n" % _py_path

        for _tool, _mid in (("g-ir-scanner", ""),
                            ("g-ir-compiler", "--includedir %s" % gir_dir)):
            _w = os.path.join(wrapper_dir, _tool)
            # g-ir-scanner 用 conan python 显式执行（不依赖 shebang/PATH 解析）；
            # g-ir-compiler 是 C 二进制，直接 exec。
            if _tool == "g-ir-scanner" and py_bin:
                _exec = "exec '%s/python3' '%s/bin/%s' %s \"$@\"\n" % (
                    py_bin, gir_pkg, _tool, _mid)
            else:
                _exec = "exec '%s/bin/%s' %s \"$@\"\n" % (gir_pkg, _tool, _mid)
            with open(_w, "w") as f:
                f.write("#!/bin/sh\n" + _env + _exec)
            os.chmod(_w, 0o755)
        self.buildenv_info.prepend_path("PATH", wrapper_dir)
        self.buildenv_info.prepend_path("PATH", os.path.join(gir_pkg, "bin"))
        self.buildenv_info.prepend_path("PATH", "/data/service/hnp/bin")
        if glib_lib:
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", glib_lib)
        if intl_lib:
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", intl_lib)
        self.buildenv_info.define("CC", "/data/service/hnp/bin/clang")

        # gobject-introspection-1.0.pc（指向正式包；girdir/typelibdir 用相对路径，
        # 使 GMenu.gir/typelib 安装进 gnome-menus 包自身的 share/gir-1.0 与
        # lib/girepository-1.0）
        with open(os.path.join(self.generators_folder, "gobject-introspection-1.0.pc"), "w") as f:
            f.write(f"prefix={gir_pkg}\n")
            f.write(f"includedir=${{prefix}}/include\nlibdir=${{prefix}}/lib\n")
            f.write(f"datadir=${{prefix}}/share\nbindir=${{prefix}}/bin\n")
            f.write(f"g_ir_scanner=%s/g-ir-scanner\n" % wrapper_dir)
            f.write(f"g_ir_compiler=%s/g-ir-compiler\n" % wrapper_dir)
            f.write(f"g_ir_generate=${{bindir}}/g-ir-generate\n")
            f.write(f"gidatadir=${{prefix}}/share/gobject-introspection-1.0\n")
            f.write(f"girdir=share/gir-1.0\n")
            f.write(f"typelibdir=lib/girepository-1.0\n")
            f.write("Name: gobject-introspection\nDescription: GI\nVersion: 1.78.1\n")
            f.write("Requires: glib-2.0, gobject-2.0, gmodule-2.0, gio-2.0\n")
            f.write(f"Libs: -L${{libdir}} -lgirepository-1.0 -lm\n")
            f.write(f"Cflags: -I${{includedir}}/gobject-introspection-1.0\n")

    def build(self):
        apply_conandata_patches(self)  # config.guess/config.sub OHOS 补丁（E007）
        # wrapper 的 PYTHONPATH 指向 gi-distutils：若 generate() 阶段未就绪（例如
        # export_sources 尚未展开），这里在 make 前补装，避免 GISCAN 再报 distutils 缺失。
        if not self._install_vendored_distutils(
                os.path.join(self.build_folder, "gi-wrappers", "gi-distutils")):
            self.output.warning("gnome-menus: gi-distutils/ unavailable at build time")
        # E011：HMDFS umask 077 导致 config.status 临时 subs*.awk Permission denied
        _cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(_cfg):
            _t = open(_cfg, encoding="utf-8", errors="replace").read()
            if "umask 077" in _t:
                open(_cfg, "w", encoding="utf-8").write(_t.replace("umask 077", "umask 022"))
        # worker 注入的 CPPFLAGS/CFLAGS/LDFLAGS 指向 ~/usr/local（可能残留旧 glib
        # 静态库）。AutotoolsToolchain 会将其写入生成的 env 脚本，configure/make
        # 经 self.run() 继承本进程环境 → 污染 Makefile 的 LDFLAGS 与 .la 的
        # dependency_libs，最终让 g-ir-scanner 探针链接命中旧静态库并报
        # g_libintl_*/pcre2_* undefined。故在 configure 前剥离这些前缀 token。
        _stripped = self._sanitize_build_flags()
        if _stripped:
            for _var, _raw in sorted(_stripped.items()):
                self.output.info("gnome-menus: stripped HNP prefix from %s (was: %s)"
                                 % (_var, _raw))
        at = Autotools(self)
        at.configure()
        at.make()
        # ── 上游官方测试（TEST_QUALITY_SPEC §3.1：autotools 包必须在 build() 末尾执行）──
        # 上游 3.36.0 实测无自动化测试：无 tests/ 目录；libmenu/desktop-directories/
        # layout/util/po 的 Makefile.am 均无 TESTS= / check_PROGRAMS / check-local
        # （util/test-menu-spec.c 注册为 noinst_PROGRAMS=gnome-menu-spec-test，是交互式
        # 手工工具而非自动化用例；m4/progtest.m4 是 gettext autoconf 宏）。
        # 仍按规范执行 make check：证明测试目标真实可跑且退出码为 0（0 用例），
        # 上游若新增用例将自动纳入 CI。
        self.run(f"{HNP_BIN}/make check")

    def package(self):
        at = Autotools(self)
        at.install()
        # 显式放置 GMenu-3.0.typelib/.gir 到包内正确位置（autotools install 可能装偏）
        for _pat, _dst_rel in (("GMenu-3.0.typelib", "lib/girepository-1.0"),
                               ("GMenu-3.0.gir", "share/gir-1.0")):
            _src = glob.glob(os.path.join(self.build_folder, "**", _pat), recursive=True)
            if _src:
                _dst_dir = os.path.join(self.package_folder, _dst_rel)
                os.makedirs(_dst_dir, exist_ok=True)
                shutil.copy2(_src[0], os.path.join(_dst_dir, _pat))
            else:
                self.output.warning("gnome-menus: %s not found in build dir" % _pat)

    def package_info(self):
        self.cpp_info.libs = ["gnome-menu-3"]
        self.cpp_info.includedirs = ["include/gnome-menus-3.0"]
        self.cpp_info.set_property("pkg_config_name", "libgnome-menu-3.0")
        # typelib 运行时位置（GI_TYPELIB_PATH）
        self.runenv_info.prepend_path(
            "GI_TYPELIB_PATH",
            os.path.join(self.package_folder, "lib", "girepository-1.0"))
