#!/usr/bin/env python3
"""Conan recipe for libnotify/0.8.3 (meson build).

libnotify 是 GNOME Desktop Notifications 库，actiona 的 notifyinstance.cpp
需要 <libnotify/notify.h>。依赖 glib/gdk-pixbuf/dbus（制品仓已有）。
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class LibnotifyConan(ConanFile):
    name = "libnotify"
    version = "0.8.3"
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
        # gdk-pixbuf/2.44.6 依赖 glib/2.84.0.1，统一版本避免版本冲突。
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
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

    def package_info(self):
        self.cpp_info.libs = ["notify"]
        self.cpp_info.set_property("pkg_config_name", "libnotify")
        self.cpp_info.requires = ["glib::glib", "gdk-pixbuf::gdk-pixbuf", "dbus::dbus"]
