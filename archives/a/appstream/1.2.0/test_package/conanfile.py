#!/usr/bin/env python3
"""Conan test_package — appstream 1.2.0 L1 消费者验证（R34 实质调用公开 API）。

PkgConfigDeps + pkg_check_modules(appstream)：配方 package_info 以组件方式声明
requires（glib 家族/libcurl/libxml2/libxmlb/libfyaml/libstemmer/zstd），
生成的 appstream.pc 携带完整 Requires，pkg-config 递归解析全部传递依赖。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AppstreamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # PkgConfigDeps 由 generate() 手动调用（须先注入 glib 无后缀组件别名：
    # appstream 传递依赖 libxmlb 组件 requires 引用 glib::gobject/gio/gmodule 旧名，
    # 而 compose 链 glib/2.84.0.1 组件键为 gobject-2.0 等 → 否则报
    # "Component 'glib::gobject' not found"，见主配方 generate() 同款处理）
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        glib_dep = self.dependencies.get("glib")
        if glib_dep is not None:
            # glib 无后缀别名（libxmlb 组件 requires 引用 glib::gobject/gio/gmodule 旧名，
            # 而 compose 链 glib/2.84.0.1 组件键为 gobject-2.0 等）
            for _suffix, _plain in (
                ("glib-2.0", "glib"),
                ("gobject-2.0", "gobject"),
                ("gio-2.0", "gio"),
                ("gmodule-2.0", "gmodule"),
            ):
                if _suffix in glib_dep.cpp_info.components and _plain not in glib_dep.cpp_info.components:
                    glib_dep.cpp_info.components[_plain] = glib_dep.cpp_info.components[_suffix]
            # R04 静态 glib（shared=False，pango 链强制）下 libappstream.a → libglib-2.0.a
            # 需要 -lintl 提供 g_libintl_gettext（proxy-libintl）；PkgConfigDeps 生成的
            # glib-2.0.pc 默认 Libs 无 intl → 消费者链接报 undefined symbol，补库修复
            glib_comp = glib_dep.cpp_info.components.get("glib-2.0")
            if glib_comp is not None and "intl" not in (glib_comp.libs or []):
                glib_comp.libs = list(glib_comp.libs or []) + ["intl"]
        from conan.tools.gnu import PkgConfigDeps
        PkgConfigDeps(self).generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # L0d 门禁要求 test() 内含 self.run()（实质执行，非空壳）；直接运行
        # 编译出的消费者二进制（conanrun 环境注入依赖库路径）
        appstream_exe = os.path.join(self.cpp.build.bindirs[0], "test_appstream")
        self.run(appstream_exe, env="conanrun", cwd=self.build_folder)
