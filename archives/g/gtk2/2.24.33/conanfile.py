#!/usr/bin/env python3
"""Conan recipe — gtk2 2.24.33 (Autotools, X11 backend).

OHOS 适配要点：
  - 构建系统: 历史 Autotools（源码树自带生成好的 configure）
  - 后端: --with-gdktarget=x11。GTK 2 没有 GTK 3 的 broadway 后端，
    x11 是 OHOS 上唯一现实目标（仓库已具备 X11 栈：xorg-server/libx11 等）。
  - configure 硬性要求 pkg-config 命中 x11 + xext + xrender 三件套，
    并对 XShape（libXext）做 AC_MSG_ERROR 级检查——libxext 必须在依赖图中。
  - 版本 pin 跟随 gtk3 栈（R36）：glib/2.84.0.1 为 pango/atk/gdk-pixbuf
    配方共同 pin，声明 2.88.x 会触发版本图冲突。
  - glib 构建工具按 gtk3 模式处理（python 脚本 shebang 改写 + pc 变量注入）。
  - OHOS 下：/system/bin/sh 执行 configure（xsane 已验证的 HMDFS 规避）、
    包内 TMPDIR、umask 000、.so 实体别名（HMDFS 无 symlink）、
    安装产物签名。
    注意：OHOS 对脚本按文件签名强制执行，工具包装必须用绝对路径的
    已签名解释器作 shebang；#!/bin/sh 与 #!/usr/bin/env 均被拒
    （设备实测 EACCES）。
"""
import glob
import os
import re
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Gtk2Conan(ConanFile):
    name = "gtk2"
    version = "2.24.33"
    description = "GTK+ 2 — multi-platform toolkit for creating graphical user interfaces (X11 backend)"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gtk.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # R36：与已发布 OHOS 二进制的 GNOME 栈对齐（全部只发 shared=True），
        # 覆盖个别依赖配方对 glib 的 shared=False pin，避免空缓存图冲突。
        for dep in ("glib", "harfbuzz", "cairo", "pango", "gdk-pixbuf", "atk", "fontconfig"):
            try:
                self.options[dep].shared = True
            except Exception:
                pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # 直接依赖；harfbuzz/pixman/freetype/zlib 等经 cairo/pango/gdk-pixbuf
        # 传递（R36，与 gtk3 配方一致）。
        # glib/2.84.0.1 为 pango/1.50.14.1.1、atk/2.38.0.1.1、gdk-pixbuf/2.44.6.1
        # 配方共同 pin 的版本——不要单方面升到 2.88.x。
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # cairo/1.18.4.1 = cairo/1.18.4 的 xlib-enabled 变体(R37 patch 递增,
        # 同一上游 tarball,ABI 为超集)。pango/gdk-pixbuf 传递 pin 1.18.4,
        # 以 force 收敛到 1.18.4.1(patch 级差异不影响 minor_mode package_id,
        # 已发布二进制仍可复用)。
        self.requires(
            "cairo/1.18.4.1",
            force=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("pango/1.50.14.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("gdk-pixbuf/2.44.6.1", transitive_headers=True, transitive_libs=True)
        self.requires("atk/2.38.0.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("fontconfig/2.18.1.1", transitive_headers=True, transitive_libs=True)
        # X11 三件套：configure 在 x11 后端硬性检查 pkg-config x11 xext xrender，
        # 且 XShape/XextFindDisplay 缺失直接 AC_MSG_ERROR。
        # libx11 用 6.4.0（SONAME 风格命名）：libxext/libxfixes/libxrandr 配方
        # 均 pin 此版本（libxrandr 带 force=True），与 X 栈保持一致；
        # libxrender/0.9.12 自身 pin 的 1.8.13 由 force 语义收敛到 6.4.0
        # （libxrandr 的 OHOS 构建已在同一图上验证过该收敛，ABI 同为 .so.6）。
        self.requires(
            "libx11/6.4.0",
            force=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxrender/0.9.12", transitive_headers=True, transitive_libs=True)
        # 可选扩展（configure 探测到即启用，缺失自动降级）：
        # xrandr>=1.2.99 / xcursor / xfixes。仓库有 libxrandr/libxfixes 的
        # OHOS 产物，libxcursor 尚无——缺失时自动降级，无需显式开关。
        self.requires("libxrandr/1.5.5", transitive_headers=True, transitive_libs=True)
        self.requires("libxfixes/6.1.0", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.5")
        self.tool_requires("autotools-dev/20240727.1-nmu1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        try:
            get(self, **sources, strip_root=True)
        except Exception as e:
            if not mirror_url:
                raise
            self.output.warning(f"Primary source failed ({e}), trying mirror")
            get(self, url=mirror_url, sha256=sources["sha256"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tools_folder = self._prepare_glib_build_tools()
        self._augment_glib_pkg_config(tools_folder)
        # gtk2 的 GLIB 模块列表要求 gmodule-no-export-2.0(真机 config.log
        # 实测缺失即 PKG_CHECK_MODULES(GLIB) 失败);glib 包只生成
        # gmodule-2.0.pc,按 gtk3 配方同款做法补转发别名。
        self._create_pkg_config_alias("gmodule-2.0.pc", "gmodule-no-export-2.0.pc", "gmodule-no-export-2.0")
        # GDK_PACKAGES 含 gio-unix-2.0(gdkapplaunchcontext-x11.c 的
        # GDesktopAppInfo),glib 包未生成该 .pc,同法补转发别名。
        self._create_pkg_config_alias("gio-2.0.pc", "gio-unix-2.0.pc", "gio-unix-2.0")

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--with-gdktarget=x11",
            # 可选 X 特性显式关闭（对应依赖未适配或为确定性）：
            "--disable-shm",        # XShm 依赖 libXext 的 XShm + SysV shm
            "--disable-xinerama",   # libxinerama 未适配
            "--with-xinput=no",     # libxi 可选，收敛依赖面
            # 打印/文档/自省：
            "--disable-cups",
            "--disable-introspection",
            "--disable-gtk-doc-html",
            # AM_PATH_GLIB_2_0 的运行型测试程序是未签名 ELF，OHOS 拒绝执行
            # （真机实测 17/18 失败同类）；关闭后仅做 pkg-config 版本检查。
            "--disable-glibtest",
        ])
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-linux-gnu",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate()

    def build(self):
        self._patch_configure_tmpdir()
        self._stage_autotools_aux_files()
        self._make_configure_executable()

        with self._build_environment().vars(self).apply():
            autotools = Autotools(self)
            if str(self.settings.os) == "OHOS":
                self._configure_for_ohos(autotools)
                # 交叉构建下 configure 将 gtk_update_icon_cache_program 置为
                # "no",gtkbuiltincache 规则执行 "no" 即 127;改指向构建产出的
                # 工具本体(链接后生成,规则执行时已存在)。
                gtk_tool = os.path.join(self.source_folder, "gtk", "gtk-update-icon-cache")
                gtk_mk = os.path.join(self.source_folder, "gtk", "Makefile")
                with open(gtk_mk, encoding="utf-8", errors="replace") as h:
                    mk_text = h.read()
                if "gtk_update_icon_cache_program = " in mk_text:
                    mk_text = re.sub(
                        r"^gtk_update_icon_cache_program = .*$",
                        "gtk_update_icon_cache_program = " + gtk_tool,
                        mk_text,
                        flags=re.M,
                    )
                    with open(gtk_mk, "w", encoding="utf-8", newline="\n") as h:
                        h.write(mk_text)
                # 裁剪 demos/tests/perf/docs:库构建不需要,且 demos 的
                # gtk-update-icon-cache 规则依赖构建期执行未签名工具
                mk = os.path.join(self.source_folder, "Makefile")
                with open(mk, encoding="utf-8", errors="replace") as h:
                    mk_text = h.read()
                import re as _re
                # gtk2 的 Makefile 把 demos/tests/perf 放在 SRC_SUBDIRS 行,
                # SUBDIRS 经 $(SRC_SUBDIRS) 间接引用;两行都必须裁剪。
                # 行首锚点+贪婪组每行只命中一次,需循环删到不动点。
                _subdirs_pat = _re.compile(r"^((?:SRC_)?SUBDIRS = .*) (demos|tests|perf|docs)(?= |$)", _re.M)
                while True:
                    _new = _subdirs_pat.sub(r"\1", mk_text)
                    if _new == mk_text:
                        break
                    mk_text = _new
                mk_text = _re.sub(r"  +", " ", mk_text)
                with open(mk, "w", encoding="utf-8", newline="\n") as h:
                    h.write(mk_text)
                self._drop_dependency_la_files()
                stub_a = self._build_intl_stub()
                self.run(f'umask 000 && make -j1 LDFLAGS="{stub_a}"', cwd=self.source_folder)
            else:
                autotools.configure()
                autotools.make(args=["-j1"])

    def package(self):
        with self._build_environment().vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self.run(
                    f"umask 000 && make install DESTDIR={shlex.quote(self.package_folder)}",
                    cwd=self.source_folder,
                )
            else:
                Autotools(self).install()
        self._sanitize_pc_files()
        if self.settings.os == "OHOS":
            if self.options.shared:
                self._materialize_shared_lib_aliases(os.path.join(self.package_folder, "lib"))
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["gtk-x11-2.0", "gdk-x11-2.0", "gailutil"]
        incs = [
            d
            for d in ("include/gtk-2.0", "lib/gtk-2.0/include", "include")
            if os.path.isdir(os.path.join(self.package_folder, d))
        ]
        self.cpp_info.includedirs = incs or ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "GTK2")
        self.cpp_info.set_property("cmake_target_name", "GTK2::GTK2")
        # 消费方（xsane 等）用 pkg-config 探测 gtk+-2.0；安装的 .pc 已经是
        # 这个名字，此处声明与之一致以便 CMakeDeps/PkgConfigDeps 消费。
        self.cpp_info.set_property("pkg_config_name", "gtk+-2.0")
        # gtk2 公共头会传递包含 pango/harfbuzz 等头（gtk.h → pango-coverage.h
        # → hb.h）;conan 不跨级传播头文件路径,消费方(含 test_package)编译
        # 会 miss。把运行依赖的包含目录并入本包 includedirs。
        dep_incs = []
        seen_inc = set(incs)
        for dep in self.dependencies.values():
            pkg_dir = getattr(dep, "package_folder", None)
            if not pkg_dir:
                continue
            for incdir in dep.cpp_info.includedirs:
                if incdir and incdir not in seen_inc:
                    seen_inc.add(incdir)
                    dep_incs.append(incdir)
        self.cpp_info.includedirs = incs + dep_incs
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # 不声明 cpp_info.requires：依赖 .pc 的 Libs 与依赖图承载链接顺序
        # （同 gtk3 配方结论）。

    # ------------------------------------------------------------------
    # glib 构建工具（gtk3 配方模式）
    # ------------------------------------------------------------------

    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _prepare_glib_build_tools(self):
        # gtk2 的 configure（AM_PATH_GLIB_2_0 内嵌宏）从 glib-2.0.pc 读取
        # glib_genmarshal / glib_mkenums 工具路径；制品仓 glib 包的这两个
        # 工具是 python 脚本，用零编译 shell wrapper 包一层再注入 pc 变量。
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        for tool in ("glib-genmarshal", "glib-mkenums"):
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                raise FileNotFoundError(f"GLib build tool missing: {src}")
            self._build_python_tool_wrapper(tool, src)
        return tools_folder

    def _build_python_tool_wrapper(self, name, script):
        # OHOS 对脚本文件按签名强制执行:`#!/bin/sh`、`#!/usr/bin/env`
        # 形式的包装在本地 conan-home 下会被拒(EACCES),只有以绝对路径
        # 的已签名解释器(python3)为 shebang 的脚本可以执行。
        # 因此把工具脚本原样复制,仅改写首行 shebang 指向当前 python3。
        tools_folder = self._glib_tools_folder()
        dst = os.path.join(tools_folder, name)
        with open(script, encoding="utf-8") as h:
            content = h.read()
        lines = content.splitlines(keepends=True)
        if lines and lines[0].startswith("#!"):
            lines[0] = "#!%s\n" % os.path.realpath(sys.executable)
        with open(dst, "w", encoding="utf-8", newline="\n") as h:
            h.write("".join(lines))
        os.chmod(dst, 0o755)

    def _augment_glib_pkg_config(self, tools_folder):
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pc):
            raise FileNotFoundError("PkgConfigDeps output missing: glib-2.0.pc")
        content = open(pc, encoding="utf-8").read()
        variables = {
            "glib_genmarshal": os.path.join(tools_folder, "glib-genmarshal"),
            "glib_mkenums": os.path.join(tools_folder, "glib-mkenums"),
        }
        block = "".join(f"{k}={v.replace(os.sep, '/')}\n" for k, v in variables.items())
        marker = "\nName:"
        if marker not in content:
            raise ValueError("Invalid glib-2.0.pc")
        content = content.replace(marker, f"\n{block}{marker}", 1)
        open(pc, "w", encoding="utf-8", newline="\n").write(content)

    def _create_pkg_config_alias(self, src_name, alias_name, pkg_name):
        # gtk3 配方同款:从既有 .pc 复制改名生成别名(如 gmodule-no-export-2.0),
        # 供上游宏按精确名称探测。
        src = os.path.join(self.generators_folder, src_name)
        alias = os.path.join(self.generators_folder, alias_name)
        if not os.path.isfile(src):
            raise FileNotFoundError(f"PkgConfigDeps missing: {src_name}")
        content = open(src, encoding="utf-8").read()
        lines = []
        for line in content.splitlines(keepends=True):
            if line.startswith("Name:"):
                if pkg_name == "gmodule-no-export-2.0":
                    lines.append("gmodule_supported=true\n\n")
                lines.append(f"Name: {pkg_name}\n")
            else:
                lines.append(line)
        open(alias, "w", encoding="utf-8", newline="\n").write("".join(lines))

    # ------------------------------------------------------------------
    # OHOS / HMDFS 处理（xsane 配方已真机验证的模式）
    # ------------------------------------------------------------------

    def _patch_configure_tmpdir(self):
        # OHOS 分布式 fs:mktemp -d 配 umask 077 会得到组/其他位全零的 0700
        # 目录,该 fs 对这类目录拒绝本用户追加写(EACCES),且 chmod 会被
        # 静默忽略(实测重启后必现);umask 000 下创建的目录组/其他位非零,
        # 写入可靠。autoconf 2.71 硬编码临时目录在 cwd(无视 TMPDIR)。
        # 改写 configure:临时目录落在 ${TMPDIR:-.}(低频目录),且不用 077。
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, encoding="utf-8", errors="replace") as h:
            content = h.read()
        replaced = [
            ('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
             'tmp=`(umask 000 && mktemp -d "${TMPDIR:-.}/confXXXXXX") 2>/dev/null` && { chmod 777 "$tmp" 2>/dev/null || true; } &&'),
            ("tmp=./conf$$-$RANDOM",
             "tmp=${TMPDIR:-.}/conf$$-$RANDOM"),
        ]
        optional = [
            ("(umask 077 && mkdir \"$tmp\")",
             "(umask 000 && mkdir \"$tmp\")"),
        ]
        changed = False
        for old, new in replaced:
            if new in content:
                continue
            if old not in content:
                raise ConanException(f"configure tmpdir pattern not found: {old[:50]}")
            content = content.replace(old, new, 1)
            changed = True
        for old, new in optional:
            if old in content and new not in content:
                content = content.replace(old, new, 1)
                changed = True
        if changed:
            with open(configure, "w", encoding="utf-8", newline="\n") as h:
                h.write(content)
            self.output.info("patched configure tmpdir to ${TMPDIR:-.} umask-000")

    def _stage_autotools_aux_files(self):
        # 2.24.33 自带的 config.guess/sub 太老，不识别 aarch64-linux-ohos；
        # 用 autotools-dev 的最新脚本覆盖源码树。
        misc = os.path.join(
            self.dependencies.build["autotools-dev"].package_folder, "share", "misc"
        )
        copy(self, "config.guess", src=misc, dst=self.source_folder)
        copy(self, "config.sub", src=misc, dst=self.source_folder)

    def _make_configure_executable(self):
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            os.chmod(configure, 0o755)

    def _build_environment(self):
        env = Environment()
        pkgconf_bin = os.path.join(
            self.dependencies.build["pkgconf"].package_folder, "bin"
        )
        env.prepend_path("PATH", pkgconf_bin)
        env.prepend_path("PATH", self._glib_tools_folder())
        env.prepend_path("PATH", os.path.join(self.dependencies["glib"].package_folder, "bin"))
        env.prepend_path("PATH", os.path.join(self.dependencies["gdk-pixbuf"].package_folder, "bin"))
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # 生成器只聚合各依赖的主 pkg_config_name——cairo 的 package_info 把
        # 名字硬编码为 "cairo" 且未声明组件,cairo-xlib.pc 不会进生成器目录,
        # configure 的 CAIRO_BACKEND 探测在 CI 上因此 miss(真机因环境巧合
        # 通过)。显式把依赖包自身的 lib/pkgconfig 垫进路径,使 cairo-xlib 等
        # 子面 .pc 的探测不依赖上游配方声明完整度。
        for _dep_name in (
            "cairo", "glib", "pango", "gdk-pixbuf", "atk", "fontconfig",
            "freetype", "libpng", "libx11", "libxext", "libxrender",
            "libxrandr", "libxfixes",
        ):
            try:
                _dep_pc = os.path.join(
                    self.dependencies[_dep_name].package_folder,
                    "lib", "pkgconfig",
                )
            except KeyError:
                continue
            if os.path.isdir(_dep_pc):
                env.append_path("PKG_CONFIG_PATH", _dep_pc)
        env.define("PKG_CONFIG", os.path.join(pkgconf_bin, "pkgconf"))
        # configure 只把部分探测到的 -I 烤进 Makefile;OHOS 无系统头文件
        # 目录,gtksocket-x11.c 的 X11/extensions/Xfixes.h 即因此 miss
        # (CI #48598 实测)。把全部依赖包含目录并入 CPPFLAGS,使每个编译
        # 单元对所有依赖头文件可见,不再依赖 configure 探测的完备性。
        inc_flags = []
        seen_inc = set()
        for _dep in self.dependencies.values():
            _pkg_dir = getattr(_dep, "package_folder", None)
            if not _pkg_dir:
                continue
            for _incdir in _dep.cpp_info.includedirs:
                if _incdir and _incdir not in seen_inc:
                    seen_inc.add(_incdir)
                    inc_flags.append(f"-I{_incdir}")
        if inc_flags:
            env.define("CPPFLAGS", " ".join(inc_flags))
        if str(self.settings.os) == "OHOS":
            env.define("CONFIG_SHELL", "/system/bin/sh")
            env.define("SHELL", "/system/bin/sh")
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler_executables = dict(compiler_executables or {})
        if str(self.settings.os) == "OHOS":
            compiler_executables.setdefault("c", "/data/service/hnp/bin/clang")
            compiler_executables.setdefault("cpp", "/data/service/hnp/bin/clang++")
        if compiler_executables.get("c"):
            env.define("CC", compiler_executables["c"])
        if compiler_executables.get("cpp"):
            env.define("CXX", compiler_executables["cpp"])
        self._define_ohos_binary_tools(env, compiler_executables)
        # TMPDIR 不在此覆盖:构建树在分布式 fs 上会随构建进程"劣化",
        # 其内子目录的文件创建/追加写会被按任务标签拒绝(真机实测)。
        # TMPDIR 由 job env.sh 提供构建树外的新鲜目录,经继承到达子进程。
        # 本机构建期需要运行依赖的 so（glib 工具等）；OHOS 原生构建时
        # 依赖库经 conanrunenv/LD_LIBRARY_PATH 注入。
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        # conan 的 run(cwd=...) 只改进程 cwd 不改 PWD 环境变量;OHOS mksh 在
        # 本地分区上 getcwd() 返回 EBADF,校验 $PWD 与实际 cwd 不符后退化为
        # getcwd → configure 报 "working directory cannot be determined"。
        # 显式对齐 PWD(真机实测修复)。
        env.define("PWD", self.source_folder)
        return env

    def _drop_dependency_la_files(self):
        # 依赖包发布的 libtool .la 烤着发布机的绝对路径,跨机即
        # "is not a valid libtool archive"(真机首轮实测需删 60 个)。
        # 链接走 pkg-config 的 .pc 与 -l,不依赖 .la;把依赖包内的
        # *.la 全部移除,避免 libtool 消费到跨机失效的归档描述。
        removed = 0
        seen = set()
        for dep in self.dependencies.values():
            pkg_dir = getattr(dep, "package_folder", None)
            if not pkg_dir:
                continue
            libdir = os.path.join(pkg_dir, "lib")
            if libdir in seen or not os.path.isdir(libdir):
                continue
            seen.add(libdir)
            for la in glob.glob(os.path.join(libdir, "**", "*.la"), recursive=True):
                os.unlink(la)
                removed += 1
        self.output.info(f"removed {removed} dependency .la files")

    def _build_intl_stub(self):
        # OHOS 无 libintl:glib 的 proxy libintl.h 把 gettext 系映射为
        # g_libintl_*(E508),OHOS libc 无实现。提供直通桩(不做翻译,
        # 构建验证足够)。-fPIC:桩会被 libtool 打进共享库。
        stub_c = os.path.join(self.build_folder, "intl-stub.c")
        stub_o = os.path.join(self.build_folder, "intl-stub.o")
        stub_a = os.path.join(self.build_folder, "libintl-stub.a")
        save(self, stub_c, "\n".join([
            "char *g_libintl_gettext(const char *m) { return (char *)m; }",
            "char *g_libintl_dgettext(const char *d, const char *m) { return (char *)m; }",
            "char *g_libintl_dcgettext(const char *d, const char *m, int c) { return (char *)m; }",
            "char *g_libintl_bindtextdomain(const char *d, const char *dir) { return (char *)dir; }",
            "char *g_libintl_bind_textdomain_codeset(const char *d, const char *c) { return (char *)c; }",
        ]))
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c") or "clang"
        self.run(f'"{cc}" -fPIC -c "{stub_c}" -o "{stub_o}"')
        ar = os.path.join(os.path.dirname(cc) if cc and os.path.sep in cc else "", "llvm-ar")
        if not os.path.isfile(ar):
            ar = "llvm-ar"
        self.run(f'"{ar}" rcs "{stub_a}" "{stub_o}"')
        return stub_a

    def _define_ohos_binary_tools(self, env, compiler_executables):
        if str(self.settings.os) != "OHOS":
            return
        compiler = compiler_executables.get("c")
        tool_dir = os.path.dirname(compiler) if compiler else "/data/service/hnp/bin"
        for env_name, tool_name in {
            "AR": "llvm-ar",
            "NM": "llvm-nm",
            "RANLIB": "llvm-ranlib",
            "STRIP": "llvm-strip",
        }.items():
            candidate = os.path.join(tool_dir, tool_name)
            if os.path.isfile(candidate):
                env.define(env_name, candidate)

    def _configure_for_ohos(self, autotools):
        shell = "/system/bin/sh"
        configure = os.path.join(self.source_folder, "configure")
        configure_args = autotools._configure_args or ""
        # PKG_CHECK_MODULES 的 conftest 链接探测在冷 worker 上因传递依赖
        # 解析偶发失败("Can't link to Pango",温热 worker 可过)。预置
        # PANGO_CFLAGS/PANGO_LIBS 后该宏跳过 pkg-config 与链接测试,直接
        # 采用查询结果;版本充分性由 conan 依赖图 pin 保证。
        pango_env = (
            'PCF="$($PKG_CONFIG --cflags pangoft2 2>/dev/null)"; '
            'PLB="$($PKG_CONFIG --libs pangoft2 2>/dev/null)"; '
            '[ -n "$PCF" ] && PANGO_CFLAGS="$PCF"; '
            '[ -n "$PLB" ] && PANGO_LIBS="$PLB"; '
            'export PANGO_CFLAGS PANGO_LIBS; '
        )
        self.run(
            f"umask 000 && {pango_env}{shlex.quote(shell)} {shlex.quote(configure)} {configure_args}",
            cwd=self.source_folder,
        )

    # ------------------------------------------------------------------
    # 打包后处理
    # ------------------------------------------------------------------

    def _sanitize_pc_files(self):
        import re
        pkg_inc = os.path.join(self.package_folder, "include")
        for pc in glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")):
            txt = open(pc, encoding="utf-8").read()
            txt = re.sub(r"^prefix=.*", f"prefix={self.package_folder}", txt, flags=re.M)
            lines = []
            for ln in txt.splitlines(True):
                if ln.startswith(("Cflags:", "Cflags.private:")):
                    head, sep, body = ln.partition(":")
                    kept = []
                    for tok in body.split():
                        m = re.match(r'^-I"?([^"]+)"?$', tok)
                        if not m:
                            kept.append(tok)
                            continue
                        p = m.group(1)
                        for var, val in (
                            ("${prefix}", self.package_folder),
                            ("${includedir}", pkg_inc),
                            ("${exec_prefix}", self.package_folder),
                            ("${datarootdir}", os.path.join(self.package_folder, "share")),
                            ("${datadir}", os.path.join(self.package_folder, "share")),
                            ("${libdir}", os.path.join(self.package_folder, "lib")),
                        ):
                            p = p.replace(var, val)
                        if os.path.isdir(p):
                            kept.append(tok)
                        else:
                            self.output.info(f"{os.path.basename(pc)}: drop non-existent -I {tok}")
                    ln = head + sep + " " + " ".join(kept) + "\n"
                lines.append(ln)
            txt = "".join(lines)
            open(pc, "w", encoding="utf-8", newline="\n").write(txt)

    def _materialize_shared_lib_aliases(self, libdir):
        # HMDFS 不支持 symlink（E316/DRAFT-2045）：libtool 安装的
        # libgtk-x11-2.0.so.0.2400.32 等需要实体副本补齐 .so.<major> 和 .so 别名。
        for real in sorted(glob.glob(os.path.join(libdir, "lib*.so.*.*.*"))):
            if not os.path.isfile(real) or os.path.islink(real):
                continue
            name = os.path.basename(real)
            root = name.split(".so.", 1)[0] + ".so"
            major = root[:-3] + ".so." + name.split(".so.", 1)[1].split(".")[0]
            for alias in (major, root):
                alias_path = os.path.join(libdir, alias)
                if os.path.lexists(alias_path):
                    if os.path.islink(alias_path):
                        os.unlink(alias_path)
                    else:
                        continue
                shutil.copyfile(real, alias_path)
            # 移除 libtool .la（内部绝对路径在包间不可移植）
        for la in glob.glob(os.path.join(libdir, "*.la")):
            os.unlink(la)

    def _sign_installed_elfs(self):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip signing")
            return
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        candidates = [shutil.which("llvm-objcopy")]
        if cc and os.path.sep in cc:
            candidates.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates if p and os.path.isfile(p)), None)
        patterns = [
            os.path.join(self.package_folder, "bin", "*"),
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ]
        cands = []
        for pat in patterns:
            cands.extend(glob.glob(pat, recursive=True))
        for binary in sorted(set(cands)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            # bin/ 里混有非 ELF 产物(如 gtk-builder-convert 是 Python 脚本),
            # 签名服务对非 ELF 文件直接报错;只签 ELF 魔数命中的文件。
            with open(binary, "rb") as h:
                if h.read(4) != b"\x7fELF":
                    continue
            if objcopy:
                self.run(f"{shlex.quote(objcopy)} --remove-section .codesign {shlex.quote(binary)} 2>/dev/null || true")
            self._sign_elf(binary)

    def _sign_elf(self, binary):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        self.run(shlex.join([signer, "sign", "-inFile", binary, "-outFile", binary, "-selfSign", "1"]))
