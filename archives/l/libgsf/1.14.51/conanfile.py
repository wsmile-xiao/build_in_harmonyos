#!/usr/bin/env python3
"""Conan recipe — libgsf 1.14.51 (Autotools).

GNOME 结构化文件格式库（OLE2/ZIP/OpenDocument 读写），鸿蒙 PC (aarch64) 适配。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.gnu.pkgconfigdeps import PkgConfigDeps
from conan.tools.layout import basic_layout


class LibgsfConan(ConanFile):
    name = "libgsf"
    version = "1.14.51"
    description = "GNOME structured file format library (OLE2/ZIP/OpenDocument)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgsf"
    url = "https://gitlab.gnome.org/GNOME/libgsf"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("libxml2/2.15.3.1")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add project-specific configure args here:
        # gdk-pixbuf 为可选依赖，OHOS 环境未安装，显式禁用
        tc.configure_args.append("--without-gdk-pixbuf")
        # glib 包自带 libintl（g_libintl_* 符号），但其 pkg-config 别名未导出 -lintl，
        # 链接 tools/gsf 等可执行文件时需补充（本地构建同因）；需带 -L 指向 glib 包 lib 目录
        # glib 静态库依赖 pcre2（gregex 等），链接 tools/gsf 时也需补充 -lpcre2-8
        # （CI 曾因 undefined symbol pcre2_match_8 等失败）
        # 注意：必须先把 extra_ldflags 全部 append 完，再调用 tc.environment()，
        # 否则 LDFLAGS 快照不会包含这些标志
        glib_dep = self.dependencies.get("glib")
        if glib_dep and glib_dep.package_folder:
            glib_lib = "{}/lib".format(glib_dep.package_folder)
            tc.extra_ldflags.append("-L{} -lintl".format(glib_lib))
        pcre2_dep = self.dependencies.get("pcre2")
        if pcre2_dep and pcre2_dep.package_folder:
            pcre2_lib = "{}/lib".format(pcre2_dep.package_folder)
            tc.extra_ldflags.append("-L{} -lpcre2-8".format(pcre2_lib))
        env = tc.environment()
        if glib_dep and glib_dep.package_folder:
            # conftest 运行时需能找到 libintl.so.8（configure 的 cross-compiling 检查）
            env.append_path("LD_LIBRARY_PATH", glib_lib)
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gsf-1"]
        # libgsf 头文件安装在 include/libgsf-1/ 子目录（autotools includedir 约定）
        self.cpp_info.includedirs = ["include/libgsf-1"]
        # 传递依赖：下游（test_package/消费者）需要 glib/libxml2/zlib 的头文件与链接
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gmodule-2.0",
            "glib::gio-2.0",
            "libxml2::libxml2",
            "zlib::zlib",
        ]
        # CMakeDeps 对缓存依赖包（glib/zlib/libxml2）的 components includedirs 快照可能为空
        # （conan 2.29.1 从远程下载包的 metadata 不含 includedirs），
        # 显式合并依赖 include 目录，保证下游编译能拿到 glib.h / libxml 头文件
        import os as _os
        dep_rel_dirs = {
            "glib": ("include", "include/glib-2.0", "lib/glib-2.0/include"),
            "libxml2": ("include", "include/libxml2"),
            "zlib": ("include",),
        }
        for dep_name, rel_dirs in dep_rel_dirs.items():
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                for rel in rel_dirs:
                    p = _os.path.join(dep.package_folder, rel)
                    if _os.path.isdir(p) and p not in self.cpp_info.includedirs:
                        self.cpp_info.includedirs.append(p)
        # libgsf 为静态库（shared=False），编译时 glib 的 G_INTL_STATIC_COMPILATION 使
        # 库内引用 g_libintl_* 符号；glib 包自带 libintl.so.8（提供 g_libintl_*），
        # 下游链接静态 libgsf 时需显式 -lintl，故把 glib 包 lib 目录与 intl 加入 libdirs/libs
        glib_dep = self.dependencies.get("glib")
        if glib_dep and glib_dep.package_folder:
            glib_lib = _os.path.join(glib_dep.package_folder, "lib")
            if _os.path.isdir(glib_lib) and glib_lib not in self.cpp_info.libdirs:
                self.cpp_info.libdirs.append(glib_lib)
            if "intl" not in self.cpp_info.libs:
                self.cpp_info.libs.append("intl")
