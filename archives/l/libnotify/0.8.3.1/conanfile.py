#!/usr/bin/env python3
"""Conan recipe for libnotify/0.8.3.1 (meson build).

libnotify 是 GNOME Desktop Notifications 库，actiona 的 notifyinstance.cpp
需要 <libnotify/notify.h>。依赖 glib/gdk-pixbuf/dbus（制品仓已有）。
"""
import os
import shutil
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class LibnotifyConan(ConanFile):
    name = "libnotify"
    version = "0.8.3.1"
    description = "GNOME Desktop Notifications library（actiona notifyinstance 依赖）"
    license = "LGPL-2.1"
    homepage = "https://gitlab.gnome.org/GNOME/libnotify"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 与 glib/2.88 生态对齐：制品仓 gdk-pixbuf/2.44.6 配方仍硬编码
        # glib/2.84.0.1 与 zlib/1.3.1.1，与其子树（libpng/libtiff/libjpeg-turbo）
        # 在依赖图中与 glib/2.88.0.1 / zlib/1.3.1.1.1.1 冲突。用 force 统一
        # 到 glib/2.88 生态（glib 保持 ABI 兼容，既有二进制可复用）。
        # 注意：override=True 不产生直接依赖边（无传递依赖覆盖时会被丢弃），
        # 而 package_info() 的 cpp_info.requires 引用了 glib::glib，故 glib
        # 必须用 force=True（强制版本且添加直接依赖）。
        self.requires("glib/2.88.0.1", transitive_headers=True, transitive_libs=True, force=True)
        self.requires("zlib/1.3.1.1.1.1", override=True)
        self.requires("gdk-pixbuf/2.44.6", transitive_headers=True, transitive_libs=True)
        self.requires("dbus/1.14.10", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["werror"] = "false"
        # tests 选项会引入 gtk+-3.0 依赖（制品仓无），禁用绕过。
        tc.project_options["tests"] = "false"
        # 文档生成依赖 docbook-xsl-ns/gi-docgen/xmlto（制品仓无），禁用。
        # generate_gir 依赖 GObject introspection 工具，禁用绕过。
        tc.project_options["introspection"] = "disabled"
        tc.project_options["man"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["docbook_docs"] = "disabled"
        if not self.options.shared:
            tc.project_options["default_library"] = "static"
        tc.generate()
        self._inject_ar_ranlib()
        # glib 的 .pc 中 glib_mkenums 指向 /bin（不存在），meson gnome 模块
        # 需要这些工具；改为指向 glib 包 bin 目录的实际工具。
        self._fix_glib_pc_vars()

    def _inject_ar_ranlib(self):
        """鸿蒙环境 meson 找不到 ar/llvm-ar，从 compiler_executables 注入。"""
        import os
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")
        if not ar:
            cc = compiler_executables.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" not in content and "[binaries]" in content:
                insertion = "[binaries]\nar = '{}'\n".format(ar)
                if ranlib:
                    insertion += "ranlib = '{}'\n".format(ranlib)
                content = content.replace("[binaries]\n", insertion, 1)
                with open(native_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _fix_glib_pc_vars(self):
        """conan 生成的 glib-2.0.pc 缺 glib_mkenums/glib_genmarshal/gobject_query
        变量（meson gnome 模块需要），补上指向 glib 包 bin 目录的真实路径。"""
        import glob
        import os
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        pc_files = glob.glob(os.path.join(self.generators_folder, "glib-2.0.pc"))
        if not pc_files:
            pc_files = glob.glob(os.path.join(
                self.dependencies["glib"].package_folder, "lib", "pkgconfig", "glib-2.0.pc"))
        for pc in pc_files:
            with open(pc, encoding="utf-8") as handle:
                content = handle.read()
            missing = []
            if "glib_mkenums" not in content:
                missing.append("glib_mkenums={}".format(os.path.join(glib_bin, "glib-mkenums")))
            if "glib_genmarshal" not in content:
                missing.append("glib_genmarshal={}".format(os.path.join(glib_bin, "glib-genmarshal")))
            if "gobject_query" not in content:
                missing.append("gobject_query={}".format(os.path.join(glib_bin, "gobject-query")))
            if missing:
                # 在 bindir= 行后追加缺失变量
                content = content.replace("bindir=${prefix}/bin",
                                          "bindir=${prefix}/bin\n" + "\n".join(missing))
                with open(pc, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        # libnotify 的 meson.build 显式 shared_library()（强制 .so，default_library
        # 不生效）；改为 library() 跟随 default_library=static，构建 .a 静态库，
        # 绕开鸿蒙动态链接器无法加载自定义 .so（namespace 忽略 LD_LIBRARY_PATH）。
        libnotify_meson = os.path.join(self.build_folder, "libnotify", "meson.build")
        if not os.path.isfile(libnotify_meson):
            libnotify_meson = os.path.join(self.source_folder, "libnotify", "meson.build")
        if os.path.isfile(libnotify_meson):
            with open(libnotify_meson, encoding="utf-8") as handle:
                content = handle.read()
            if "shared_library(" in content and "library(" not in content:
                content = content.replace("shared_library(", "library(")
                with open(libnotify_meson, "w", encoding="utf-8") as handle:
                    handle.write(content)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        # OHOS loader fix: meson install's depfixer X's out the build rpath
        # (absolute conan-cache path) in the installed .so, which corrupts the
        # ELF so the OHOS loader refuses to map it (EACCES). Restore the
        # pristine build .so (with valid rpath) over the installed one.
        import glob as _glob
        # package() 时 self.build_folder 指向 build-release 上级，找不到就沿
        # package 目录向上递归搜索 build-release 里的原始 .so
        search_roots = [os.path.dirname(self.package_folder), self.build_folder]
        build_sos = []
        for root in search_roots:
            if root and os.path.isdir(root):
                build_sos += _glob.glob(os.path.join(root, "**", "libnotify.so.4.0.0"),
                                        recursive=True)
        dst = os.path.join(self.package_folder, "lib", "libnotify.so.4.0.0")
        # 优先 build 目录下的原始产物（带有效 rpath），跳过 destdir 里被
        # depfixer 处理过的文件（rpath 被 'X' 覆盖 -> OHOS loader EACCES）
        build_sos = [s for s in build_sos if "build" in s and s != dst]
        for src in sorted(build_sos):
            if os.path.isfile(src) and os.path.isfile(dst):
                self.output.info("OHOS fix: restoring pristine libnotify.so.4.0.0 from %s" % src)
                shutil.copy2(src, dst)

    def package_info(self):
        self.cpp_info.libs = ["notify"]
        self.cpp_info.set_property("pkg_config_name", "libnotify")
        self.cpp_info.requires = ["glib::glib", "gdk-pixbuf::gdk-pixbuf", "dbus::dbus"]
