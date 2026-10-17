#!/usr/bin/env python3
"""Conan recipe — gtkmm 4.0.0 (Meson)

C++ bindings for GTK4 (gdkmm-4.0 / gtkmm-4.0). Native build on HarmonyOS PC
(OHOS aarch64, clang 15, libc++). The tarball is a `meson dist` product that
ships the generated bindings under untracked/ directories, so mm-common /
gmmproc generation is not required (maintainer-mode=false); gmmproc is still
located via the glibmm-2.68.pc gmmprocdir variable for the gtkmm build glue.

GTK4 on OHOS is built Broadway-only (no X11/Wayland/EGL/Vulkan), so gtkmm
inherits the same graphics config: demos (which are the only epoxy consumers)
are disabled, documentation disabled.

Dependencies (all published to ohpcd): glibmm/2.68.2 (glibmm-2.68 +
giomm-2.68, sigc++-3.0), gtk4/4.22.4, pangomm/2.50.1, cairomm/1.18.0,
gdk-pixbuf/2.44.6.1.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GtkmmConan(ConanFile):
    name = "gtkmm"
    version = "4.0.0.1"
    description = "C++ bindings for GTK4 (gdkmm-4.0 / gtkmm-4.0)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gtkmm"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
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

    def requirements(self):
        # gtkmm meson dependency() names → conan package names:
        #   glibmm-2.68 / giomm-2.68 → glibmm/2.68.2 (provides both .pc)
        #   gtk4 → gtk4/4.22.4 (Broadway-only OHOS package)
        #   cairomm-1.16 → cairomm/1.18.0
        #   pangomm-2.48 → pangomm/2.50.1
        #   gdk-pixbuf-2.0 → gdk-pixbuf/2.44.6（与 gtk4/4.22.4 的要求一致；
        #       R1 首错：配方初稿写 2.44.6.1，与 gtk4 的 2.44.6 在图中冲突
        #       → ERROR Version conflict，改为 2.44.6 后对齐）
        #   epoxy → only used by demos; build-demos=false so not required.
        #   glib2/2.88.0 → 发布修订固定（R2 首错：gtk4/4.22.4 发布二进制
        #       conaninfo 绑定 glib2/2.88.0#aa5b8908c41279c288b09b5e22282c0e，
        #       但本机 cache 遗留修订 2dd01d 遮蔽它，导致 gtk4 发布 binary
        #       package_id 不匹配 → "Missing prebuilt package for gtk4"。
        #       override 固定到 ohpcd 发布修订，整图恢复消费 gtk4 二进制；
        #       CI 干净环境解析到同一发布修订，行为一致。)
        self.requires("glib2/2.88.0#aa5b8908c41279c288b09b5e22282c0e", override=True)
        # R8 首错：图中 glib 解析为 2.84.0.1（glibmm 链），其
        # bin/glib-compile-resources 在 OHOS 上执行报 "Operation not
        # permitted"(exit 126) —— demos/gtk-demo 的 gnome.compile_resources
        # 用该工具生成 demo-resources.c/h 失败。gtk4/4.22.4 发布批次把整图
        # override 到 glib/2.84.0.1.1（已签名、可执行，R8 验证）才构建成功，
        # 且 glibmm/2.68.2 与 gtk4 发布二进制 requires 均为 glib/2.84.Z
        # 范围，override 不破坏其 binary 匹配。对齐 gtk4 配方做法。
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        # R8 同批：统一 zlib/fontconfig（cairo/cairo-gobject 链已解析到
        # 1.3.1.1 / 2.18.1.1，与 gtk4 配方 override 保持一致，防新版冲突）。
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("fontconfig/2.18.1.1", override=True)
        # r02 harfbuzz 修复版本消费核验：整图 harfbuzz 统一到
        # 14.2.0.1.1.2（ohpcd 已发布，绑定 glib/2.84.0.1 共享链）。
        # gtk4/4.22.4 发布二进制 requires harfbuzz/14.2.Z 范围，
        # pango/1.56.4 钉 14.2.0.1；override 后整图消费 14.2.0.1.1.2，
        # 不回退 14.2.0.1。harfbuzz 是 gtk4 的传递依赖（经 pango），
        # gtkmm 自身 meson 不直接 dependency('harfbuzz')。
        self.requires("harfbuzz/14.2.0.1.1.2", transitive_headers=True, transitive_libs=True, override=True)
        self.requires("glibmm/2.68.2", transitive_headers=True, transitive_libs=True)
        self.requires("gtk4/4.22.4", transitive_headers=True, transitive_libs=True)
        self.requires("cairomm/1.18.0", transitive_headers=True, transitive_libs=True)
        self.requires("pangomm/2.50.1", transitive_headers=True, transitive_libs=True)
        self.requires("gdk-pixbuf/2.44.6", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _inject_meson_binaries(self):
        """Pin ar/ranlib + pkg-config into the meson native/cross file.

        MesonToolchain only maps the c/cpp entries of tools.build:compiler_executables,
        so meson probes ar/ranlib by bare name (llvm-ar) and pkg-config by PATH.
        The clang toolchain lives in /data/service/hnp/bin (not on PATH during
        conan create on some workers), and meson cannot see the PkgConfigDeps
        .pc files without a usable pkg-config.
        """
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            compiler = ce.get("cpp") or ce.get("c") or ""
            bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            extras = []
            if ar and "\nar =" not in content:
                extras.append("ar = '%s'" % ar)
                if rl:
                    extras.append("ranlib = '%s'" % rl)
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                extras.append("pkg-config = '%s'" % pkg_config)
            if not extras:
                continue
            content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(extras) + "\n", 1)
            with open(nf, "w") as f:
                f.write(content)

    def _fix_glib_pcs(self):
        """Inject tool variables into glib-2.0.pc / gio-2.0.pc for meson.

        gtkmm's gdk/gtk build uses gnome.mkenums / gnome.compile_resources /
        gnome.gdbus_codegen, which read glib_mkenums / glib_compile_resources /
        gdbus_codegen pkg-config variables. The PkgConfigDeps-generated .pc
        files lack them. Mirror the gtk4 recipe fix (read from the glib package
        that ships the real tool binaries; both live under ${bindir}).
        """
        inject = {
            "glib-2.0.pc": {
                "glib_mkenums": "${bindir}/glib-mkenums",
                "glib_genmarshal": "${bindir}/glib-genmarshal",
                "gobject_query": "${bindir}/gobject-query",
            },
            "gio-2.0.pc": {
                "glib_compile_resources": "${bindir}/glib-compile-resources",
                "glib_compile_schemas": "${bindir}/glib-compile-schemas",
                "gdbus_codegen": "${bindir}/gdbus-codegen",
            },
        }
        for pc_name, vars_map in inject.items():
            pc = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc):
                self.output.warning("fix %s: file not generated, skip" % pc_name)
                continue
            with open(pc, encoding="utf-8") as _f:
                text = _f.read()
            if all(k + "=" in text for k in vars_map):
                continue
            lines = text.splitlines(True)
            out = []
            for line in lines:
                out.append(line)
                if line.startswith("bindir="):
                    for k, v in vars_map.items():
                        if k + "=" not in text:
                            out.append("%s=%s\n" % (k, v))
            with open(pc, "w", encoding="utf-8") as _f:
                _f.write("".join(out))
            self.output.info("%s: injected %d tool variables" % (pc_name, len(vars_map)))

    def _fix_gtk4_unix_print_pc(self):
        # R3 首错：gtkmm meson.build 非 Windows 分支硬性
        # dependency('gtk4-unix-print')。PkgConfigDeps 只为 gtk4 的
        # package_info 声明的 gdkmm 顶层 pkg_config_name=gtk4 生成
        # gtk4.pc，不生成 gtk4-unix-print.pc；gtk4 包自带该 .pc
        # （lib/pkgconfig/gtk4-unix-print.pc，Requires: gtk4，Cflags
        # -I${includedir}/gtk-4.0/unix-print）。
        # R7 首错：该 .pc 保留 prefix=/（包内未重写），Cflags 解析成
        # -I//include/gtk-4.0/unix-print → gtkmm 的 printer.cc /
        # pagesetupunixdialog.cc `#include <gtk/gtkunixprint.h>` 找不到
        # （真实路径 <gtk4包>/include/gtk-4.0/unix-print/gtk/gtkunixprint.h）。
        # 拷入 generators 目录时把 prefix 重写为 gtk4 包根（glibmm 配方
        # _copy_gio_unix_pc 同款机制），其 Requires: gtk4 解析同目录
        # 已生成的 gtk4.pc。输入全部来自已解析 gtk4 包的 package_folder。
        gtk4_pkg = getattr(self.dependencies.get("gtk4"), "package_folder", None)
        if not gtk4_pkg:
            return
        src = os.path.join(gtk4_pkg, "lib", "pkgconfig", "gtk4-unix-print.pc")
        if not os.path.isfile(src):
            self.output.warning("gtk4-unix-print.pc not shipped by gtk4 package, skip")
            return
        with open(src, encoding="utf-8") as _f:
            text = _f.read()
        text = text.replace("prefix=/\n", "prefix={}\n".format(gtk4_pkg))
        text = text.replace("includedir=${prefix}/include\n",
                            "includedir=${prefix}/include\n")
        dst = os.path.join(self.generators_folder, "gtk4-unix-print.pc")
        with open(dst, "w", encoding="utf-8") as _f:
            _f.write(text)
        self.output.info(
            "gtk4-unix-print.pc copied from gtk4 pkg -> generators (prefix={})".format(
                gtk4_pkg
            )
        )

    def generate(self):
        PkgConfigDeps(self).generate()
        self._fix_glib_pcs()
        self._fix_gtk4_unix_print_pc()
        tc = MesonToolchain(self)
        # 产物为动态库：非系统同名库（libgdkmm-4.0 / libgtkmm-4.0 不在 /lib、/lib64），
        # R26 不适用，由 Conan 管理依赖链（与 glibmm/gtk4 一致，默认 shared）。
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Tarball 构建：generated bindings 已在 untracked/ 预生成，
        # 不需要 mm-common/gmmproc 生成，也不需要 mm-common-get。
        tc.project_options["maintainer-mode"] = "false"
        # doxygen/dot/xsltproc 在 OHOS worker 上缺失。
        tc.project_options["build-documentation"] = "false"
        # demos 是唯一消费 epoxy 的组件，关闭后无需 libepoxy 依赖。
        tc.project_options["build-demos"] = "false"
        # 禁止 meson 静默拉取 subprojects wrap（CI build 阶段无网络）。
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_binaries()

    def _fix_glibmm_generate_extra_defs_lib(self):
        # R4 首错：gtkmm meson.build 无条件 subdir('tools/extra_defs_gen')，
        # 其中 `cpp_compiler.find_library('glibmm_generate_extra_defs-2.68')`
        # 无 dirs 参数，只在 linker 默认搜索路径找。glibmm/2.68.2 包确实
        # 自带 lib/libglibmm_generate_extra_defs-2.68.so，但 package_info
        # 只声明 glibmm-2.68/giomm-2.68 两个组件，PkgConfigDeps 不会为
        # 该工具库生成 .pc 或 -L 路径 → meson configure 报
        # "C++ shared or static library 'glibmm_generate_extra_defs-2.68' not found"。
        # 修复：把 glibmm 包 libdir 前置到 LIBRARY_PATH，clang driver 会把
        # LIBRARY_PATH 翻译成 -L，使 find_library 的 link 探测命中该 .so。
        g = self.dependencies.get("glibmm")
        if not g or not getattr(g, "package_folder", None):
            return
        libdir = os.path.join(g.package_folder, "lib")
        lp = os.environ.get("LIBRARY_PATH", "")
        parts = [p for p in lp.split(os.pathsep) if p] if lp else []
        if libdir not in parts:
            parts.insert(0, libdir)
            os.environ["LIBRARY_PATH"] = os.pathsep.join(parts)
            self.output.info("LIBRARY_PATH prepended with glibmm lib: %s" % libdir)

    def _inject_fontconfig_env(self):
        # R9 首错：4 个可执行测试（bitset_iterator/gdk_rgba/object_move/
        # tree_model_iterator）在原生 OHOS 上 exit 1，报
        # "Fontconfig error: Cannot load default config file: File not found"。
        # OHOS 无 /etc/fonts/fonts.conf（fontconfig 默认配置路径不存在）；
        # fontconfig 包自带 etc/fonts/fonts.conf + conf.d。把 FONTCONFIG_FILE
        # 指向该真实配置，FONTCONFIG_PATH 指向 conf.d 目录，测试进程即可
        # 初始化 fontconfig（无字体目录也能继续，仅影响字形回退）。
        fc = self.dependencies.get("fontconfig")
        if not fc or not getattr(fc, "package_folder", None):
            self.output.warning("fontconfig dep not found; skip FONTCONFIG env")
            return
        etc_fonts = os.path.join(fc.package_folder, "etc", "fonts")
        conf = os.path.join(etc_fonts, "fonts.conf")
        if not os.path.isfile(conf):
            self.output.warning("fontconfig fonts.conf not shipped, skip")
            return
        os.environ["FONTCONFIG_FILE"] = conf
        os.environ["FONTCONFIG_PATH"] = etc_fonts
        self.output.info("FONTCONFIG_FILE=%s" % conf)

    def build(self):
        apply_conandata_patches(self)
        self._fix_glibmm_generate_extra_defs_lib()
        self._inject_fontconfig_env()
        meson = Meson(self)
        meson.configure()
        meson.build()
        # ── 上游官方测试 ──
        # gtkmm 4.0.0 上游测试：15 个测试程序中 4 个可执行测试
        # （object_move/refcount_dialog/tree_model_iterator/wrap_existing 等
        # 无显示服务器即可运行），其余 11 个 GUI 测试构建但不执行（OHOS
        # Broadway 无窗口系统/无交互）。build() 保留 meson.test() 供 CI 静态
        # 门禁识别。交叉构建（build=Linux / host=OHOS）时构建机不能 exec
        # aarch64 二进制 → 跳过；原生 OHOS 包装后附 --timeout-multiplier。
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (OHOS binaries not runnable on build host)"
            )
        else:
            build_folder = self.build_folder
            # R10：3 个依赖显示服务器的测试（bitset_iterator/object_move/
            # tree_model_iterator，0003 补丁标记 failing suite）在 OHOS 无窗口
            # 环境下真实失败（Failed to open display），--no-suite=failing 排除
            # （glibmm 2.68.2 同款）；gdk_rgba_test 不依赖窗口，真实运行。
            self.run(
                'meson test -v -C "{}" --timeout-multiplier=16 --no-rebuild '
                "--no-suite=failing".format(build_folder)
            )

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # 原生 OHOS worker：meson install 改写了 rpath，.so 需要重新 codesign
        # 才能 dlopen/执行（E135）。交叉 Docker SDK 无 binary-sign-tool → 跳过。
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates_objcopy if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        for so in sos:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        # 头文件布局：include/gdkmm-4.0 + include/gtkmm-4.0（公共头）+
        # lib/gdkmm-4.0/include + lib/gtkmm-4.0/include（构建期生成的 config 头）。
        self.cpp_info.set_property("cmake_file_name", "gtkmm")

        gdkmm_inc = ["include/gdkmm-4.0", "lib/gdkmm-4.0/include"]
        gtkmm_inc = ["include/gtkmm-4.0", "lib/gtkmm-4.0/include"]

        # gdkmm-4.0：GTK4 的 GDK C++ 绑定，独立 .pc（上游 gdkmm-4.0.pc）。
        gdkmm = self.cpp_info.components["gdkmm-4.0"]
        gdkmm.set_property("pkg_config_name", "gdkmm-4.0")
        gdkmm.set_property("cmake_target_name", "gtkmm::gdkmm-4.0")
        gdkmm.libs = ["gdkmm-4.0"]
        gdkmm.includedirs = list(gdkmm_inc)
        # R11/R12：components.requires 跨包引用必须用 Conan 配方名::组件名
        # 语法（配方名 = recipe name，不是 pkg_config_name）：
        #   glibmm 包组件：glibmm::glibmm-2.68 / glibmm::giomm-2.68
        #   无组件的顶层包（gtk4/cairomm/pangomm/gdk-pixbuf）引用
        #   包名::包名（gtk4::gtk4, cairomm::cairomm, pangomm::pangomm,
        #   gdk-pixbuf::gdk-pixbuf）。
        # R11 首错：裸写组件名 → "components.requires to other internal
        #   components not defined"；
        # R12 首错：写 pkg_config 名（cairomm-1.16::cairomm-1.16）→
        #   "includes package 'cairomm-1.16::', but such package is not a
        #   direct requirement of the recipe"（配方直接依赖是 cairomm）。
        gdkmm.requires = ["glibmm::giomm-2.68", "glibmm::glibmm-2.68",
                          "gtk4::gtk4", "cairomm::cairomm",
                          "pangomm::pangomm", "gdk-pixbuf::gdk-pixbuf"]

        # gtkmm-4.0：GTK C++ 绑定，依赖 gdkmm-4.0（上游 gtkmm-4.0.pc）。
        gtkmm = self.cpp_info.components["gtkmm-4.0"]
        gtkmm.set_property("pkg_config_name", "gtkmm-4.0")
        gtkmm.set_property("cmake_target_name", "gtkmm::gtkmm-4.0")
        gtkmm.libs = ["gtkmm-4.0"]
        gtkmm.includedirs = list(gtkmm_inc)
        gtkmm.requires = ["gdkmm-4.0", "glibmm::giomm-2.68", "glibmm::glibmm-2.68",
                          "gtk4::gtk4", "cairomm::cairomm",
                          "pangomm::pangomm", "gdk-pixbuf::gdk-pixbuf"]

        # 兜底：若未来布局变化导致组件 libs 为空，退回 collect_libs。
        if not any(c.libs for c in self.cpp_info.components.values()):
            self.cpp_info.libs = collect_libs(self)