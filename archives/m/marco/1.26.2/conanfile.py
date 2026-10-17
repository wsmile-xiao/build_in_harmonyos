#!/usr/bin/env python3
"""Conan recipe — marco 1.26.2 (MATE window manager) for OpenHarmony PC (aarch64).

构建系统: autotools (release tarball 自带 configure / Makefile.in)

平台适配要点（详见 notes.md / PR 说明）:

1) GDK-X11 兼容层。OHPCD 制品仓的 gtk/3.24.43 是 broadway 后端构建: 不含
   ``gdk/gdkx.h``、不导出 ``gdk_x11_*`` 符号、cairo 也没有 cairo-xlib。
   marco 是纯 X11 客户端（11 个源文件 include ``<gdk/gdkx.h>``，
   ``GDK_DISPLAY_XDISPLAY`` 100 处、``GDK_WINDOW_XID`` 13 处），因此
   ``patches/0001`` 新增 ``src/x11-compat/gdk/gdkx.h`` 与
   ``src/x11-compat/marco-x11-compat.c``（单例 X 连接 + XID 映射 + 错误陷阱
   + X 事件过滤器分发），本配方把它编译成 ``marco-x11-compat.o`` 并追加到
   ``LIBS``，从而不改动 Makefile.am / Makefile.in 等生成文件（R6）: 补丁只
   新增源文件，构建接入全部在配方内完成（CI 无 automake，见
   references/iron-rules.md R6 与 SKILL §7）。

2) libcanberra-gtk3。marco 的 ``MARCO_PC_MODULES`` 无条件要求
   ``libcanberra-gtk3``，但制品仓 libcanberra/0.30 用 ``--disable-gtk3``
   构建（无 canberra-gtk.h / 无 libcanberra-gtk3.pc）。``patches/0002``
   新增 ``src/x11-compat/canberra-gtk.h``（等价实现 ca_gtk_context_get()），
   本配方生成同名的 shim .pc 指向真实 libcanberra/0.30 + 兼容层头目录，
   保持上游源码零改动。

3) startup-notification: 制品仓未发布 libstartup-notification-1.0，使用上游
   官方开关 ``--disable-startup-notification``（同 pidgin/2.14.14 与
   libwnck3/43.3 先例）。libSM/libICE 已发布，会话管理保持启用。

4) GLib gsettings: ``src/Makefile.am`` 的 ``@GSETTINGS_RULES@`` 需要
   glib-compile-schemas，配方从 glib 包取该工具、自签（OHOS 拒绝执行未签名
   ELF）并把生成的 gio-2.0.pc 的 ``glib_compile_schemas`` 变量指向签名副本。
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, mkdir)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# pkg-config 模块名 → conan 包名（marco configure.ac 用 PKG_CHECK_MODULES /
# AC_CHECK_LIB 探测，必须让包提供对应的 .pc 名）
PKG_CONFIG_NAMES = {
    "glib": "glib-2.0",
    "gtk": "gtk+-3.0",
    "gdk-pixbuf": "gdk-pixbuf-2.0",
    "libx11": "x11",
    "libxext": "xext",
    "libxrender": "xrender",
    "libxrandr": "xrandr",
    "libxcursor": "xcursor",
    "libxinerama": "xinerama",
    "libxdamage": "xdamage",
    "libxcomposite": "xcomposite",
    "libxfixes": "xfixes",
    "libice": "ice",
    "libsm": "sm",
    "libxres": "xres",
}


class MarcoConan(ConanFile):
    name = "marco"
    version = "1.26.2"
    description = ("MATE window manager: X11 compositing window manager "
                   "(GTK 3) for OpenHarmony PC")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/mate-desktop/marco"
    url = "https://github.com/mate-desktop/marco"
    topics = ("window-manager", "x11", "gtk", "mate", "desktop")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/**"

    # ── 依赖 ────────────────────────────────────────────────────────────
    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 直接依赖（版本与制品仓已发布 OHOS armv8 binary 精确对齐；R36）
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)
        # 保持 gtk/3.24.43 的 cairo-gobject/1.18.4.2 pin：换成 xlib 版
        # 1.18.4.3 会把 libx11/libxrender 带进 gtk 的 embed 依赖信息，
        # 使制品仓的 gtk 预编译 binary package_id 失配（需源码重建）。
        # Cairo-Xlib 由补丁 0005 的兼容层提供。
        self.requires("cairo-gobject/1.18.4.2", transitive_headers=True,
                      transitive_libs=True)
        self.requires("pango/1.50.14.1.1", transitive_headers=True,
                      transitive_libs=True)
        self.requires("gdk-pixbuf/2.44.6.1", transitive_headers=True,
                      transitive_libs=True)
        self.requires("atk/2.38.0.1.1", transitive_headers=True, transitive_libs=True)
        # 事件声音（XDG sound theme；gtk3 模块缺失，见 docstring 第 2 点）
        self.requires("libcanberra/0.30", transitive_headers=True,
                      transitive_libs=True)
        # X11 客户端库（窗口管理、合成器、光标、多屏）
        # libx11 用 override 压掉 libxrender/0.9.12 配方的 libx11/1.8.13 传递
        # pin（同 cairo-gobject/1.18.4.3 与 cairo/1.18.4 的处理）
        self.requires("libx11/6.4.0", override=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxrender/0.9.12", transitive_headers=True,
                      transitive_libs=True)
        self.requires("libxrandr/1.5.5", transitive_headers=True,
                      transitive_libs=True)
        self.requires("libxcursor/1.2.3", transitive_headers=True,
                      transitive_libs=True)
        self.requires("libxinerama/1.1.6", transitive_headers=True,
                      transitive_libs=True)
        self.requires("libxdamage/1.1.6.1", transitive_headers=True,
                      transitive_libs=True)
        self.requires("libxcomposite/0.4.6", transitive_headers=True,
                      transitive_libs=True)
        self.requires("libxfixes/6.1.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxres/1.2.1", transitive_headers=True, transitive_libs=True)
        # 会话管理（libSM/libICE 已发布，保持 HAVE_SM 路径可用）
        self.requires("libice/1.1.2", transitive_headers=True, transitive_libs=True)
        self.requires("libsm/1.2.6", transitive_headers=True, transitive_libs=True)
        # 传递依赖版本冲突调和（与 cairo/pango/gdk-pixbuf 图一致）
        self.requires("pixman/0.46.4", override=True)
        self.requires("libjpeg-turbo/3.2.0", override=True)
        self.requires("fontconfig/2.18.1.1", override=True)
        self.requires("expat/2.8.2.1", override=True)

    def build_requirements(self):
        # YELP_HELP_INIT: configure 强制检查 itstool（帮助文档翻译构建）
        self.tool_requires("itstool/2.0.7")

    def layout(self):
        basic_layout(self)

    # ── 源码 ────────────────────────────────────────────────────────────
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── 生成阶段 ────────────────────────────────────────────────────────
    def generate(self):
        pkg_config = PkgConfigDeps(self)
        for dep, pc_name in PKG_CONFIG_NAMES.items():
            pkg_config.set_property(dep, "pkg_config_name", pc_name)
        pkg_config.generate()

        tools_folder = self._prepare_native_tools()
        self._augment_glib_pcs(tools_folder)
        shim_folder = self._write_canberra_gtk3_shim()

        toolchain = AutotoolsToolchain(self)
        # 制品仓未发布 libstartup-notification-1.0（上游官方开关）
        toolchain.configure_args.append("--disable-startup-notification")
        # 依赖头/库搜索路径：configure 的 AC_CHECK_LIB / AC_CHECK_HEADER
        # （XShape/XSync/Xrandr/Xinerama/XComposite/XRender/SM）需要显式
        # -L/-I，否则全部探测失败 → marco 会静默裁掉这些窗口管理能力。
        private_libdir = self._prepare_private_libdir()
        toolchain.extra_ldflags.append(f"-L{private_libdir}")
        # 兼容层头目录必须在依赖头之前（<cairo/cairo-xlib.h>、<gdk/gdkx.h>、
        # <canberra-gtk.h> 都优先命中兼容层版本）
        toolchain.extra_cflags.append(f"-I{self._compat_include_dir()}")
        for dependency in self.dependencies.host.values():
            cpp_info = dependency.cpp_info.aggregated_components()
            for includedir in cpp_info.includedirs:
                if includedir:
                    toolchain.extra_cflags.append(f"-I{includedir}")
            for libdir in cpp_info.libdirs:
                if libdir:
                    toolchain.extra_ldflags.append(f"-L{libdir}")
        toolchain.generate()
        self._toolchain = toolchain

        environment = Environment()
        environment.prepend_path("PATH", tools_folder)
        environment.prepend_path("PKG_CONFIG_PATH", shim_folder)
        # configure 的链接探测会运行 conftest，需要能加载私有前缀里的依赖 .so
        environment.prepend_path("LD_LIBRARY_PATH", private_libdir)
        tmpdir = os.path.join(self.build_folder, "tmp")
        mkdir(self, tmpdir)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        environment.vars(self).save_script("marco_build_env")

    # ── 编译阶段 ────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        self._apply_configure_transforms()
        compat_objects = self._compile_x11_compat()
        # 兼容层调用真实 libcanberra（ca_context_create/change_props）；
        # marco-message / marco-window-demo 的 LIBS 不含 canberra，故随兼容层
        # 一起追加（对 libmarco-private / marco / marco-theme-viewer 无害）
        canberra_libdir = os.path.join(
            self.dependencies["libcanberra"].package_folder, "lib")
        # make 命令行变量必须整体加引号，否则空格会把 -L/-l 拆成 make 选项
        libs = (f'"{" ".join(compat_objects)} '
                f'-L{canberra_libdir} -lcanberra"')

        autotools = Autotools(self)
        autotools.configure()
        # 兼容层目标文件经 LIBS 追加到每条链接命令末尾（libtool 链接
        # libmarco-private 与 marco/marco-message 等需要一个 X 连接的单例实现）
        autotools.make(args=[f"LIBS={libs}"])
        # make check：autotools 路径无 TESTS/check_PROGRAMS（0 用例），
        # 保留执行以留 L1c 痕迹
        autotools.make(target="check", args=[f"LIBS={libs}"])
        # 上游自检测试（R51 第 2 步实跑）：src/core/testboxes.c 的 14 个用例
        self._run_upstream_self_tests()

    # ── 打包 ────────────────────────────────────────────────────────────
    def _run_upstream_self_tests(self):
        """真实执行上游自检测试程序 `testboxes`（R51 第 2 步：可运行环境实跑）。

        上游 `src/core/testboxes.c` 提供 14 个自检用例（`test_area`、
        `test_intersect`、`test_equal`、`test_overlap_funcs`、`test_basic_fitting`、
        `test_regions_okay`、`test_region_fitting`、`test_clamping_to_region`、
        `test_clipping_to_region`、`test_shoving_into_region`、
        `test_find_onscreen_edges`、`test_find_nonintersected_xinerama_edges`、
        `test_gravity_resize`、`test_find_closest_point_to_line`，共 73 条
        `g_assert`），只依赖纯几何代码、不需要 X display，因此可在 OHOS 无 X
        环境下真实运行；上游未把它注册为 meson test()（noinst_PROGRAMS，仅随
        `make all` 构建），本配方在 build() 内显式执行它，把上游自检纳入门禁。

        运行时只需依赖共享库可见：用 build_folder 私有 .so 目录
        （`_prepare_private_libdir`，R49）作为 LD_LIBRARY_PATH，不引用任何
        未定义的 shell 变量（R33）。
        """
        src_dir = os.path.join(self.build_folder, "src")
        binary = os.path.join(src_dir, "testboxes")
        if not os.path.isfile(binary):
            raise ConanException(
                f"upstream self-test binary is missing: {binary}")
        libdir = os.path.join(self.build_folder, "marco-libdir")
        log_path = os.path.join(self.build_folder, "upstream-testboxes.log")
        self.run(f'LD_LIBRARY_PATH="{libdir}" ./testboxes > "{log_path}" 2>&1',
                 cwd=src_dir)
        with open(log_path, encoding="utf-8", errors="replace") as handle:
            output = handle.read()
        if "All tests passed." not in output:
            raise ConanException(
                "upstream testboxes self-test did not report success:\n"
                + output[-2000:])
        # 上游 1.26.2 的 testboxes 恰有 14 个 test_* 用例（每个打印 "<name> passed."）
        case_lines = [line for line in output.splitlines()
                      if line.endswith(" passed.") and not line.startswith("All ")]
        if len(case_lines) != 14:
            raise ConanException(
                f"unexpected upstream self-test case count: {len(case_lines)} "
                f"(expected 14)\n" + "\n".join(case_lines))
        self.output.info(
            "upstream self-test: testboxes 14/14 cases passed (All tests passed.)")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        self._compile_gsettings_schema()
        if str(self.settings.os) == "OHOS":
            self._sign_package_elfs()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "marco")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ── 辅助实现 ────────────────────────────────────────────────────────
    def _compat_include_dir(self):
        return os.path.join(self.source_folder, "src", "x11-compat")

    def _compat_sources(self):
        return [
            os.path.join(self._compat_include_dir(), "marco-x11-compat.c"),
            os.path.join(self._compat_include_dir(), "marco-cairo-xlib.c"),
        ]

    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "marco-native-tools")

    def _prepare_native_tools(self):
        """把构建期需要的依赖自带工具复制+自签（OHOS 拒绝执行未签名 ELF）。

        - glib-compile-schemas: src/Makefile.am 的 @GSETTINGS_RULES@ 使用
        - gdk-pixbuf-csource: configure 强制检查（GTK 主题/光标资源生成）
        """
        tools_folder = self._glib_tools_folder()
        mkdir(self, tools_folder)
        tools = {
            "glib": ("glib-compile-schemas",),
            "gdk-pixbuf": ("gdk-pixbuf-csource",),
        }
        for dependency, names in tools.items():
            bindir = os.path.join(self.dependencies[dependency].package_folder, "bin")
            for name in names:
                source = os.path.join(bindir, name)
                if not os.path.isfile(source):
                    raise ConanException(f"{dependency} build tool missing: {source}")
                signed = os.path.join(tools_folder, name)
                shutil.copyfile(source, signed)
                os.chmod(signed, 0o755)
                if str(self.settings.os) == "OHOS":
                    self._sign_elf(signed)
        return tools_folder

    def _prepare_private_libdir(self):
        """R49 私有前缀：依赖 .so 的实体副本目录（刻意不含 .la）。

        制品仓里的 X11 包带 libtool ``.la`` 归档描述文件，其
        ``dependency_libs`` 记录的是打包机的绝对路径（``~/.cache/conan2/...``、
        ``~/.conan2/p/b/...``，均已不存在），libtool 优先使用 .la 就会
        "cannot find the library .../libxcb.la"。把依赖的 .so 实体副本放进
        build_folder 下的私有目录并置于 -L 首位（LDFLAGS 最前），libtool
        找不到 .la 便直接使用 .so，无需改动共享缓存或系统前缀（R49/E524）。
        """
        libdir = os.path.join(self.build_folder, "marco-libdir")
        mkdir(self, libdir)
        # cairo 与 cairo-gobject 打包同一个 SONAME libcairo.so（前者 xlib
        # disabled、后者 enabled），必须让 cairo-gobject 的副本胜出，
        # 所以它在最后覆盖（同名文件后写覆盖先写）。
        preferred_last = ("cairo-gobject",)
        ordered, deferred = [], []
        for key, dependency in self.dependencies.host.items():
            name = str(getattr(getattr(key, "ref", key), "name", key))
            if name in preferred_last:
                deferred.append(dependency)
            else:
                ordered.append(dependency)
        ordered.extend(deferred)
        for dependency in ordered:
            package_folder = dependency.package_folder
            if not package_folder:
                continue
            source_dir = os.path.join(package_folder, "lib")
            if not os.path.isdir(source_dir):
                continue
            for name in sorted(os.listdir(source_dir)):
                if ".so" not in name:
                    continue
                source = os.path.join(source_dir, name)
                target = os.path.join(libdir, name)
                if os.path.isfile(target) or not os.path.isfile(source):
                    continue
                shutil.copyfile(source, target)  # 跟随符号链接，落成实体文件
        return libdir

    def _augment_glib_pcs(self, tools_folder):
        """修正 PkgConfigDeps 生成的 glib .pc 两处：

        1) glib-2.0.pc 的 Libs 缺 ``-lintl``：本仓 glib 的 ``g_libintl_*``
           符号由同包的 libintl.so 提供，而 PkgConfigDeps 生成的最小 .pc 丢掉
           了该库，导致 marco-message 等链接期 undefined symbol
           （libwnck3/43.3 的 _augment_glib_pc 同款修正）。
        2) gio-2.0.pc 缺 ``glib_compile_schemas`` 变量：configure.ac 的
           GLIB_GSETTINGS 用 ``pkg-config --variable`` 取工具路径，缺失即
           "glib-compile-schemas not found"，故插入指向签名副本的变量。
        """
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            raise ConanException("PkgConfigDeps did not generate glib-2.0.pc")
        with open(glib_pc, encoding="utf-8") as handle:
            lines = handle.read().splitlines(keepends=True)
        patched = []
        for line in lines:
            if line.startswith("Libs:") and "-lintl" not in line.split():
                line = line.rstrip("\r\n") + " -lintl\n"
            patched.append(line)
        with open(glib_pc, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("".join(patched))

        path = os.path.join(self.generators_folder, "gio-2.0.pc")
        if not os.path.isfile(path):
            raise ConanException("PkgConfigDeps did not generate gio-2.0.pc")
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        target = os.path.join(tools_folder, "glib-compile-schemas")
        variable = f"glib_compile_schemas={target}\n"
        lines = []
        replaced = False
        for line in content.splitlines(keepends=True):
            if line.startswith("glib_compile_schemas="):
                line = variable
                replaced = True
            elif not replaced and line.startswith("Name:"):
                lines.append(variable + "\n")
                replaced = True
            lines.append(line)
        if not replaced:
            lines.append(variable)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("".join(lines))

    def _write_canberra_gtk3_shim(self):
        """生成 libcanberra-gtk3.pc（指向真实 libcanberra + 兼容层头目录）。

        上游 marco 的 MARCO_PC_MODULES 无条件要求 libcanberra-gtk3；制品仓
        libcanberra/0.30 未构建 gtk3 模块（无该 .pc 与 canberra-gtk.h）。
        补丁 0002 提供等价头，本 shim 让 pkg-config 把它的头目录与真实
        libcanberra 的链接参数一起交给 marco。
        """
        shim_folder = os.path.join(self.build_folder, "marco-pkgconfig-shim")
        mkdir(self, shim_folder)
        canberra = self.dependencies["libcanberra"]
        canberra_libdir = os.path.join(canberra.package_folder, "lib")
        content = "\n".join([
            "prefix=/",
            "exec_prefix=${prefix}",
            "libdir=" + canberra_libdir,
            "includedir=" + self._compat_include_dir(),
            "",
            "Name: libcanberra-gtk3",
            "Description: XDG sound theme API for GTK+ 3 "
            "(HarmonyOS compatibility shim, see marco patches/0002)",
            "Version: 0.30",
            "Requires: libcanberra",
            "Libs: -L${libdir} -lcanberra",
            "Cflags: -I${includedir}",
            "",
        ])
        with open(os.path.join(shim_folder, "libcanberra-gtk3.pc"),
                  "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        return shim_folder

    def _apply_configure_transforms(self):
        """对 release tarball 里预生成的 configure 做两处同源机械替换。

        两处都是 configure.ac 已表达的意图（patches/0003、0004），但 release
        tarball 带的是生成产物 configure，本机与 CI 都没有 yelp-tools +
        gettext + libtool 的完整 m4 链（重生成不可行，同 libcanberra/0.30 的
        configure-ohos 先例），故在配方里做同源替换；任一处匹配不到即报错，
        避免静默失效。

        1) zenity 存在性检查：改为警告（zenity 是运行时可选的对话框助手，
           src/core/util.c 按名字查找；制品仓未发布 zenity）。
        2) config.status 的临时目录创建：`mktemp -d` 在 HMDFS 上产出 2700 目录
           （chmod 被文件系统忽略、group 位不可恢复），之后 config.status
           在其中创建 subs1.awk 被拒（EACCES: can't create ... subs1.awk），
           整份 configure 以 "could not setup config files machinery" 失败。
           改为走 configure 自带的 mkdir 回退分支（mkdir 产物被文件系统
           归一化为 2771，可写）。
        """
        path = os.path.join(self.source_folder, "configure")
        with open(path, encoding="utf-8") as handle:
            content = handle.read()

        zenity_old = ('if test x"$ZENITY" = xno; then\n'
                      '  as_fn_error $? "zenity not found in your path - needed for '
                      'dialogs" "$LINENO" 5\n'
                      'fi')
        zenity_new = ('if test x"$ZENITY" = xno; then\n'
                      '  { printf "%s\\n" "$as_me:${as_lineno-$LINENO}: WARNING: '
                      'zenity not found in your path - dialogs will be unavailable" >&5\n'
                      'printf "%s\\n" "$as_me: WARNING: zenity not found in your path '
                      '- dialogs will be unavailable" >&2;}\n'
                      'fi')
        mktemp_old = ('  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
                      '  test -d "$tmp"')
        mktemp_new = ('  tmp=\n'
                      '  test -d "$tmp"')

        for old, new, label in ((zenity_old, zenity_new, "zenity check"),
                                (mktemp_old, mktemp_new, "config.status tempdir")):
            if old not in content:
                raise ConanException(
                    f"unexpected configure layout: {label} pattern not found")
            content = content.replace(old, new, 1)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _dependency_includedirs(self):
        includedirs = [self._compat_include_dir()]
        for dependency in self.dependencies.host.values():
            cpp_info = dependency.cpp_info.aggregated_components()
            for includedir in cpp_info.includedirs:
                if includedir and includedir not in includedirs:
                    includedirs.append(includedir)
        return includedirs

    def _compile_x11_compat(self):
        """编译 GDK-X11 兼容层为目标文件（不修改 Makefile.am，见 docstring）。"""
        toolchain = getattr(self, "_toolchain", None) or AutotoolsToolchain(self)
        variables = toolchain.vars()
        compiler = variables.get("CC") or os.environ.get("CC")
        if not compiler:
            raise ConanException("no C compiler available for the X11 compat layer")
        build_folder = os.path.join(self.build_folder, "marco-x11-compat")
        mkdir(self, build_folder)
        objects = []
        for source in self._compat_sources():
            target = os.path.join(
                build_folder, os.path.basename(source)[:-2] + ".o")
            command = [shlex.quote(compiler), "-c", shlex.quote(source),
                       "-o", shlex.quote(target), "-fPIC"]
            for flag in (variables.get("CPPFLAGS") or "").split():
                command.append(flag)
            for flag in (variables.get("CFLAGS") or "").split():
                command.append(flag)
            for includedir in self._dependency_includedirs():
                command.append(f"-I{shlex.quote(includedir)}")
            self.run(" ".join(command), cwd=self.source_folder)
            if not os.path.isfile(target):
                raise ConanException(f"failed to build the compat layer: {target}")
            objects.append(target)
        return objects

    def _compile_gsettings_schema(self):
        """补一份 gschemas.compiled。

        autotools 的 GSETTINGS_RULES 在 DESTDIR 安装时会跳过编译（留给最终
        安装位置），包内因此只有 org.mate.marco.gschema.xml；这里用自签的
        glib-compile-schemas 就地生成编译产物，运行期 GSETTINGS_SCHEMA_DIR
        指向包内目录即可直接生效。
        """
        schema_dir = os.path.join(self.package_folder, "share", "glib-2.0",
                                  "schemas")
        tool = os.path.join(self._glib_tools_folder(), "glib-compile-schemas")
        if not os.path.isdir(schema_dir) or not os.path.isfile(tool):
            return
        self.run(f'"{tool}" "{schema_dir}"')

    def _sign_elf(self, path):
        """OHOS 内核拒绝执行未签名 ELF（clinfo / xeyes 同款自签）。"""
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            return
        if os.path.isfile(objcopy):
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
        self.run(f'{signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass  # HMDFS 上 chmod 可能不可用（E046）

    def _sign_package_elfs(self):
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if not os.path.isfile(path) or os.path.islink(path):
                    continue
                with open(path, "rb") as handle:
                    magic = handle.read(4)
                if magic != b"\x7fELF":
                    continue
                self._sign_elf(path)
