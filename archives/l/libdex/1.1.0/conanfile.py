#!/usr/bin/env python3
"""Conan recipe for libdex 1.1.0 — Meson build, GIO-based async library.

libdex is a Deferred Execution library for GNOME (async/fiber primitives on
top of GLib). Built with Meson; requires glib (gio-unix-2.0 >= 2.87) and,
on OHOS where libc lacks makecontext/getcontext/swapcontext, libucontext.
"""

import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibdexConan(ConanFile):
    name = "libdex"
    version = "1.1.0"
    description = "libdex 1.1.0 - Deferred Execution for GNOME (async/fiber primitives)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libdex"
    url = "https://download.gnome.org/sources/libdex/1.1/libdex-1.1.0.tar.xz"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # gio-unix-2.0 >= 2.87 (glib_req_version in upstream meson.build)
        # transitive_headers: libdex 公开头文件包含 glib 头，消费者需可见
        # glib/2.88.3.1：修复 gio-2.0.pc 缺 gdbus_codegen 变量 + gdbus-codegen
        # 工具随包交付（PR #9454），-Dgdbus=enabled 实例化 test-dbus 的前置。
        self.requires("glib/2.88.3.1", transitive_headers=True, transitive_libs=True)
        # OHOS libc 无 makecontext/getcontext/swapcontext，由 libucontext 提供
        if self.settings.os == "OHOS":
            self.requires(
                "libucontext/1.5.2", transitive_headers=True, transitive_libs=True
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # 上游默认：introspection enabled / vapi true / pygobject true /
        # liburing auto / gdbus auto —— OHOS 上关闭无意义或不可用项
        tc.project_options["introspection"] = "disabled"
        tc.project_options["vapi"] = "false"
        tc.project_options["pygobject"] = "false"
        tc.project_options["docs"] = "false"
        tc.project_options["examples"] = "true"
        tc.project_options["tests"] = "true"
        tc.project_options["liburing"] = "disabled"
        tc.project_options["sysprof"] = "false"
        # -Dgdbus=enabled：glib/2.88.3.1 已交付 gdbus-codegen 工具与
        # gdbus_codegen 变量，test-dbus 11 用例得以实例化并实际运行。
        tc.project_options["gdbus"] = "enabled"
        tc.project_options["eventfd"] = "auto"
        self._inject_absolute_binutils(tc)
        tc.generate()
        self._write_gio_unix_pc()

    def _inject_absolute_binutils(self, tc):
        # MesonToolchain 的 ar/strip 默认取自 AR/STRIP 构建环境变量（裸名），
        # 远端 CI worker 的 meson setup 期 PATH 不含该裸名 → "Unknown linker(s)
        # [['llvm-ar']]" / "No such file or directory: 'llvm-ar'"。从 C 编译器
        # 所在目录解析 LLVM binutils 的绝对路径显式覆盖，保证本地与 CI 一致。
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c") or ""
        compiler_directory = os.path.dirname(compiler) if compiler else ""
        if compiler_directory and not tc.ar:
            for attr, tool in (("ar", "llvm-ar"), ("strip", "llvm-strip")):
                candidate = os.path.join(compiler_directory, tool)
                if os.path.isfile(candidate):
                    setattr(tc, attr, candidate)

    def _write_gio_unix_pc(self):
        # glib 配方未声明 gio-unix 组件，PkgConfigDeps 不产出 gio-unix-2.0.pc；
        # 上游 meson.build 在非 Windows 平台依赖它（头文件在 glib 包
        # include/gio-unix-2.0，API 在 libgio-2.0）。手工写入 generators 目录
        # （conan meson native 文件的 pkg_config_path 指向该目录）。
        glib_dep = self.dependencies.get("glib")
        if not glib_dep or not glib_dep.package_folder:
            return
        pc_path = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        with open(pc_path, "w", encoding="utf-8") as _pc:
            _pc.write(
                "prefix={0}\n"
                "libdir=${{prefix}}/lib\n"
                "includedir=${{prefix}}/include\n"
                "\n"
                "Name: GIO unix specific APIs\n"
                "Description: unix specific headers for glib I/O library\n"
                "Version: 2.88.3\n"
                "Requires: gobject-2.0, gio-2.0\n"
                "Cflags: -I${{prefix}}/include/gio-unix-2.0\n"
                "Libs: -L${{libdir}} -lgio-2.0\n".format(glib_dep.package_folder)
            )

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()

    def package(self):
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.install()

    def package_info(self):
        self.cpp_info.libs = ["dex-1"]
        self.cpp_info.set_property("pkg_config_name", "libdex-1")
        self.cpp_info.set_property("cmake_file_name", "libdex")
        self.cpp_info.set_property("cmake_target_name", "libdex::libdex")
        self.cpp_info.includedirs = ["include/libdex-1"]
        # 传递依赖：libdex 公开头文件包含 glib-object.h，消费者需 glib 组件可见
        # （组件名取 glib 配方 cpp_info.components 键：glib/gobject/gio）
        self.cpp_info.requires = [
            "glib::glib",
            "glib::gobject",
            "glib::gio",
        ]
        if self.settings.os == "OHOS":
            # libucontext 提供 ucontext 上下文切换实现（libucontext.a 与
            # libucontext_posix.a），需传递给消费者
            self.cpp_info.requires.append("libucontext::libucontext")
            # 原子操作内置于编译器运行时（OHOS 无独立 libatomic）
            self.cpp_info.system_libs.append("ucontext")
            self.cpp_info.system_libs.append("ucontext_posix")

    def _build_environment(self):
        environment = Environment()
        # glib 配方未导出 gio-unix-2.0 组件，meson 需从 glib 包内 pkgconfig
        # 目录发现 gio-unix-2.0.pc（PkgConfigDeps 生成的 pc 不含它）
        glib_pkgconfig = os.path.join(
            self.dependencies["glib"].package_folder, "lib", "pkgconfig"
        )
        environment.prepend_path("PKG_CONFIG_PATH", glib_pkgconfig)
        # 上游测试临时目录：创建当前用户可写的专用目录（HMDFS 无 0700 语义时
        # 由 TMPDIR 指引到设备真实挂载点）
        temporary_directory = os.path.join(self.build_folder, "tmp")
        os.makedirs(temporary_directory, exist_ok=True)
        environment.define_path("TMPDIR", temporary_directory)
        environment.define_path("TMP", temporary_directory)
        environment.define_path("TEMP", temporary_directory)
        # glib 构建工具（glib-mkenums 等）位于 glib 包 bin/
        environment.prepend_path(
            "PATH", os.path.join(self.dependencies["glib"].package_folder, "bin")
        )
        return environment
