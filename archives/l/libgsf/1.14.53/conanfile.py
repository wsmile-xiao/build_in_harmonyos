#!/usr/bin/env python3
"""Conan recipe — libgsf 1.14.53

GNOME Structured File Library. Pure C library for reading/writing
structured file formats (OLE2, ZIP, tar, etc.). Used by abiword plugins
(docbook, epub) via libgsf-1.pc pkg-config.
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibgsfConan(ConanFile):
    name = "libgsf"
    version = "1.14.53"
    description = "GNOME Structured File Library (OLE2/ZIP/tar)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgsf"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游 Gentoo/Debian 声明: glib >=2.36, libxml2 >=2.4.16, zlib
        # R36/CI 对齐: 依赖版本必须用仓库已适配配方(registry 已发布或 --build=missing
        # 可从仓库配方编译),否则 CI Worker 干净环境报 "not resolved"
        self.requires("glib/2.84.0")
        self.requires("libxml2/2.15.3")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps: autotools 的 configure 用 pkg-config 发现依赖
        # (glib-2.0/gobject-2.0/gio-2.0/libxml-2.0),必须生成依赖的 .pc 文件
        # 并注入 PKG_CONFIG_PATH,否则 configure 报 "No package 'glib-2.0' found"。
        PkgConfigDeps(self).generate()
        # pcre2 配方的 .la 文件 libdir='//lib'(--prefix=/ 产生),libtool 链接
        # libgsf 时解析 pcre2 .la 报 "not a valid libtool archive" → patch
        # pcre2.pc 的 Libs 为 .a 绝对路径,让 libtool 不解析 .la。
        # 注意: 不能硬编码 ~/.conan2/p/b/pcre2*/p 本机路径——CI 干净环境
        # 哈希目录不同会漏匹配,必须从 self.dependencies 拿真实 package_folder。
        import glob as _glob
        _pcre2_lib = ""
        try:
            _pcre2_lib = os.path.join(self.dependencies["pcre2"].package_folder, "lib")
        except Exception:
            pass
        if not _pcre2_lib:
            _fallback = _glob.glob("/storage/Users/currentUser/.conan2/p/b/pcre2*/p/lib")
            if _fallback:
                _pcre2_lib = _fallback[0]
        if _pcre2_lib and os.path.isdir(_pcre2_lib):
            _pcre2_pc = os.path.join(self.generators_folder, "pcre2.pc")
            if os.path.exists(_pcre2_pc):
                with open(_pcre2_pc, "r", encoding="utf-8") as _f:
                    _pc = _f.read()
                if "-lpcre2-8" in _pc and ".a" not in _pc:
                    _pc = _pc.replace(
                        "Libs: -L\"${libdir}\" -lpcre2-8 -lpcre2-posix",
                        "Libs: -L\"${{libdir}}\" {}/libpcre2-8.a {}/libpcre2-posix.a".format(
                            _pcre2_lib, _pcre2_lib))
                    with open(_pcre2_pc, "w", encoding="utf-8") as _f:
                        _f.write(_pc)
        # glib-2.0.pc 的 Libs 带 "-L/lib -l:ld-musl-aarch64.so.1"(glib 配方把
        # musl loader 写入 system_libs),ld.lld 对 "-l:filename" 语法在无
        # 显式搜索路径时找不到 → 改为绝对路径 /lib/ld-musl-aarch64.so.1;
        # 且 glib 2.84.0 是 R26 static 包(仅 .a),若 -L 顺序中本机旧 glib
        # 2.68.3 包(.so)在前,链接器误用旧 .so 导致运行时符号缺失 →
        # 把 glib 库全部改为 .a 绝对路径强制静态链接
        _glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.exists(_glib_pc):
            with open(_glib_pc, "r", encoding="utf-8") as _f:
                _pc = _f.read()
            # 同样不能用硬编码 ~/.conan2/p/b/glibfebb*/p 探测——CI 干净环境
            # 哈希目录不同会漏匹配(glib-2.0.pc 的 -l:ld-musl-aarch64.so.1
            # 未替换 → ld.lld unable to find library)。从 dependencies 拿真实路径。
            _glib_cur = ""
            try:
                _glib_cur = os.path.join(self.dependencies["glib"].package_folder, "lib")
            except Exception:
                pass
            if not _glib_cur:
                _fallback = _glob.glob("/storage/Users/currentUser/.conan2/p/b/glibfebb*/p/lib")
                if _fallback:
                    _glib_cur = _fallback[0]
            if _glib_cur and os.path.isdir(_glib_cur):
                _gl = _glib_cur
                _pc = _pc.replace("-l:ld-musl-aarch64.so.1",
                                  "/lib/ld-musl-aarch64.so.1")
                for _libn in ("glib-2.0", "gobject-2.0", "gio-2.0",
                              "gmodule-2.0", "gthread-2.0"):
                    _pc = _pc.replace(
                        "-l{}".format(_libn),
                        "{}/lib{}.a".format(_gl, _libn))
                with open(_glib_pc, "w", encoding="utf-8") as _f:
                    _f.write(_pc)
        # libgsf configure.ac 的 libgsf_reqs 单独检查 "gobject-2.0" 和 "gio-2.0"
        # (PKG_CHECK_MODULES 按包名逐个查),而 PkgConfigDeps 只生成聚合的
        # glib-2.0.pc → 显式补写 gobject-2.0.pc / gio-2.0.pc。
        # 注意: 不能依赖探测 ~/.conan2/p/b/glib*/p 包目录——本机源码构建的 glib
        # 是 R26 static 包(仅 .a),但 CI 从 registry 下载的二进制包(tgz 解压)
        # 目录结构不同,libgobject-2.0.a/.so 探测会漏匹配(CI 实测报
        # "No package 'gobject-2.0' found",即使 PKG_CONFIG_PATH 已注入)。
        # 改为从 PkgConfigDeps 生成的 glib-2.0.pc 派生: 复用其 prefix/
        # includedir/Cflags,仅改 Name/Libs(→ -lgobject-2.0 / -lgio-2.0)。
        _glib_pc_src = os.path.join(self.generators_folder, "glib-2.0.pc")
        _glib_pc_cflags = "-I${includedir} -I${includedir1}"
        _glib_pc_prefix = "${pcfiledir}/../.."
        if os.path.exists(_glib_pc_src):
            with open(_glib_pc_src, "r", encoding="utf-8", errors="ignore") as _f:
                _glib_pc_text = _f.read()
            # 提取 Cflags(含 includedir 展开)供派生 .pc 复用
            _m = re.search(r"^Cflags:\s*(.+)$", _glib_pc_text, re.M)
            if _m:
                _glib_pc_cflags = _m.group(1).strip()
        _pc_extra = {
            "gobject-2.0": "gobject-2.0",
            "gio-2.0": "gio-2.0",
        }
        for _name, _libname in _pc_extra.items():
            _pf = os.path.join(self.generators_folder, _name + ".pc")
            if not os.path.exists(_pf):
                _pc_text = (
                    "prefix={}\n"
                    "libdir=${{prefix}}/lib\n"
                    "includedir=${{prefix}}/include/glib-2.0\n"
                    "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                    "\n"
                    "Name: {}\n"
                    "Description: Conan package: {}\n"
                    "Version: 2.84.0\n"
                    "Libs: -L${{libdir}} -l{}\n"
                    "Cflags: {}\n"
                    "Requires: glib-2.0\n"
                ).format(_glib_pc_prefix, _name, _name, _libname, _glib_pc_cflags)
                with open(_pf, "w", encoding="utf-8") as _f:
                    _f.write(_pc_text)
        tc = AutotoolsToolchain(self)
        # 禁用可选依赖: gdk-pixbuf (图形), introspection (GObject 反射)
        tc.configure_args.append("--disable-gdk-pixbuf")
        tc.configure_args.append("--disable-introspection")
        # 不构建自带的 thumbnailer (图形相关)
        tc.configure_args.append("--disable-thumbnailer")
        # 不构建自带工具 (只输出库)
        tc.configure_args.append("--disable-tools")
        # OHOS 不被 config.guess 识别,且 HMDFS 沙箱拦 config.guess 写 TMPDIR
        # 临时文件(Permission denied: .../tmp/cgEcJAnf/dummy.c)→ 显式传
        # --build/--host 跳过 config.guess(CI Worker 干净环境无本机 hack,
        # 必须写入配方,否则 configure 报 "cannot guess build type")。
        tc.configure_args.append("--build=aarch64-linux")
        tc.configure_args.append("--host=aarch64-linux")
        # PkgConfigDeps 生成的 .pc 在 generators_folder,但 conanbuild env 未自动
        # 注入 PKG_CONFIG_PATH → 显式注入指向 generators_folder(含 libgsf-1.pc/
        # glib-2.0.pc/gobject-2.0.pc/gio-2.0.pc),否则 configure 的
        # PKG_CHECK_MODULES 报 "No package 'gobject-2.0' found"(CI 实测)。
        tc.configure_args.append("PKG_CONFIG_PATH={}".format(self.generators_folder))
        tc.generate()

    def build(self):
        # Patch config.guess/config.sub for OHOS (R15)
        self._patch_config_for_ohos()

        apply_conandata_patches(self)

        # 记忆坑①: 鸿蒙安全框架拦脚本子进程在新目录写文件。autoconf 的
        # config.status 默认用 AS_TMPDIR 在 build 目录建 ./confXXXXXX 临时目录,
        # 子进程写 subs1.awk 被拦 → "could not setup config files machinery"。
        # 修法同 bird/abiword-plugin-epub 配方: 配方(主进程) os.makedirs 预建
        # 可写目录,再把 configure 里嵌入的 config.status 模板 ac_tmp 改指它。
        # ac_tmp=$tmp 同时出现在 configure 与内嵌 config.status 模板,改 configure 即两者都修。
        if self.settings.os == "OHOS":
            import tempfile
            fixed_tmp = os.path.join(tempfile.gettempdir(), "libgsf-ac-tmp")
            os.makedirs(fixed_tmp, exist_ok=True)
            _cfg_path = os.path.join(self.source_folder, "configure")
            if os.path.exists(_cfg_path):
                with open(_cfg_path, "r", encoding="utf-8") as _f:
                    _cfg = _f.read()
                if "ac_tmp=$tmp" not in _cfg:
                    raise ConanException(
                        "E114: ac_tmp=$tmp pattern not found in configure; "
                        "autoconf may have changed the template")
                _cfg = _cfg.replace("ac_tmp=$tmp", "ac_tmp={}".format(fixed_tmp))
                # config.status 的 trap 在退出时 rm -fr "$ac_tmp" 会删掉预建目录,
                # 后续轮次就找不到目录。把 trap 改为只透传退出码,不再删除
                # (目录由配方主进程管理,残留无害)。
                _old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
                _new_trap = 'exit $exit_status'
                if _old_trap in _cfg:
                    _cfg = _cfg.replace(_old_trap, _new_trap)
                with open(_cfg_path, "w", encoding="utf-8") as _f:
                    _f.write(_cfg)
                os.chmod(_cfg_path, 0o755)
                self.output.info("  [ok] Patched configure: ac_tmp -> {} (HMDFS)".format(fixed_tmp))

            # libgsf configure.ac 无 --disable-tools/--disable-thumbnailer/
            # --disable-tests 选项(CI 实测 unrecognized),tools/gsf.c 用 glib
            # 2.84 的 gi18n.h 无条件展开 gettext() → clang -Werror
            # implicit-function-declaration 编译失败。patch 顶层 Makefile.in
            # 的 SUBDIRS,去掉非库必需子目录,只保留 po gsf gsf-win32 doc。
            _mf_in = os.path.join(self.source_folder, "Makefile.in")
            if os.path.exists(_mf_in):
                with open(_mf_in, "r", encoding="utf-8") as _f:
                    _mf = _f.read()
                _old_subdirs = "SUBDIRS = po gsf gsf-win32 doc tools tests thumbnailer python"
                _new_subdirs = "SUBDIRS = po gsf gsf-win32 doc"
                if _old_subdirs in _mf:
                    _mf = _mf.replace(_old_subdirs, _new_subdirs)
                    with open(_mf_in, "w", encoding="utf-8") as _f:
                        _f.write(_mf)
                    self.output.info("  [ok] Disabled tools/tests/thumbnailer/python in Makefile.in")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub for OHOS (R15)."""
        skill_root = os.environ.get("OHC_SKILL_ROOT", "")
        if skill_root:
            script = os.path.join(skill_root, "scripts", "patch-autotools-ohos.pl")
            if os.path.exists(script):
                self.output.info("Patching config.guess/config.sub with skill script")
                for f in ("config.guess", "config.sub"):
                    path = os.path.join(self.source_folder, f)
                    if os.path.exists(path):
                        subprocess.run(["perl", script, path], check=True)
                return
        self.output.info("OHC_SKILL_ROOT not set or script not found, skipping autotools patch")

    def package(self):
        autotools = Autotools(self)
        # P3 review: 移除冗余 copy —— autotools.install() 用 DESTDIR 已把
        # libgsf-1.pc 装到 package_folder/lib/pkgconfig（上游 Makefile install 段），
        # 手动 copy 源路径 (build_folder/libgsf) 可疑且重复。
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gsf-1"]
        # 头文件实际装在 include/libgsf-1/gsf/gsf.h (autotools 标准布局),
        # 必须显式声明 includedirs,否则下游 #include <gsf/gsf.h> 找不到
        self.cpp_info.includedirs = ["include/libgsf-1"]
        # pkg-config name for downstream PKG_CHECK_MODULES
        self.cpp_info.set_property("pkg_config_name", "libgsf-1")
        # Requires for downstream pkg-config chain
        # glib/2.84.0 无 components,conan 2 对无组件包用 pkg::pkg 自引用格式
        # (裸包名会被当作本包内部组件报 not defined)
        self.cpp_info.requires = ["glib::glib", "libxml2::libxml2", "zlib::zlib"]
