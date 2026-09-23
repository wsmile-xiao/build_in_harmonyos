#!/usr/bin/env python3
"""Conan recipe — ayatana-indicator-notifications 23.10.1 (CMake).

Ayatana 通知指示器服务：D-Bus session service，负责会话内通知的收集、
展示与"免打扰"（DND）切换，由 ayatana-indicator 框架加载。

HarmonyOS PC 适配说明：
  - 构建系统为 CMake，顶层 CMakeLists.txt 通过
    pkg_check_modules(SERVICE_DEPS REQUIRED glib-2.0 gio-2.0 gio-unix-2.0
    libayatana-common) 解析依赖。
  - PkgConfigDeps 生成各依赖 .pc 后需两个补充：
    * glib 配方只提供 glib-2.0/gio-2.0/gobject-2.0 等 .pc，缺 gio-unix-2.0.pc
      → 从 glib 包目录合成（参考 gtk+ 配方 _write_gio_unix_pc 模式）。
    * glib 的 proxy-libintl 提供 g_libintl_* 符号，glib-2.0.pc 未列 -lintl
      → 追加 -lintl（与 libayatana-common 配方 _augment_glib_pkg_config 一致）。
  - 系统同名库（glib/libayatana-common）均为共享库由 conan 依赖链管理，
    无需静态化（R26 仅要求不得将同名 .so 输出到系统路径）。
  - OHOS 无 intltool 可执行 → 0001 补丁新增 SKIP_PO 选项跳过 po/ 子目录。
  - data/CMakeLists.txt 原 XDG_AUTOSTART_DIR=/etc/xdg/autostart 为绝对路径，
    会写出 package 目录之外 → 0002 补丁改为
    ${CMAKE_INSTALL_PREFIX}/etc/xdg/autostart。
  - main.c 增加 --version/--help 支持：D-Bus 服务在 OHOS PC 无 session bus，
    原始程序会进入 g_main_loop 阻塞；加参数处理使服务可被 smoke test 验证
    （test_package 以 conanrun 环境运行）。
  - cmake-extras 提供 GSettings CMake 模块（find_package(GSettings) +
    add_schema()），作为构建期依赖引入，其包目录注入 CMAKE_PREFIX_PATH。
  - data/CMakeLists.txt 的 systemd 单元段：OHOS 无 systemd，
    pkg_check_modules(SYSTEMD systemd) 自然失败、该段自动跳过。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps


class AyatanaIndicatorNotificationsConan(ConanFile):
    name = "ayatana-indicator-notifications"
    version = "23.10.1"
    description = "Ayatana indicator notifications service — D-Bus notification session service"
    license = "GPL-3.0"
    homepage = "https://github.com/AyatanaIndicators/ayatana-indicator-notifications"
    url = "https://github.com/AyatanaIndicators/ayatana-indicator-notifications"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libayatana-common/0.9.13", transitive_headers=True, transitive_libs=True)
        # cmake-extras 提供 GSettings/Intltool CMake 模块（无原生编译，纯数据包）
        self.requires("cmake-extras/1.9")

    def build_requirements(self):
        # gettext 提供 msgmerge/msgfmt：GSettingsConfig.cmake 强制 find_package(Gettext
        # REQUIRED)（FindGettext 需 GETTEXT_MSGMERGE_EXECUTABLE），OHOS 系统无该工具，
        # CI 干净环境因此失败；gettext/0.22.5.1 为已合并的 application 工具包，
        # conan 会将其中 bin/ 注入 CMAKE_PROGRAM_PATH（FindGettext 按此查找）。
        self.tool_requires("gettext/0.22.5.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 构建沙箱的 LDFLAGS 环境变量指向 ~/usr/local/lib（内含旧版静态 glib
        # 2.88），若泄漏进链接行会以静态旧 glib 覆盖 conan 共享依赖，导致
        # ffi/pcre2/intl 等未定义符号。这里显式清空 LDFLAGS/CFLAGS/CXXFLAGS，
        # 编译器与链接标志完全由 Conan Toolchain 注入（R33）。
        build_env = Environment()
        for var in ("LDFLAGS", "CFLAGS", "CXXFLAGS", "CPPFLAGS"):
            build_env.define(var, "")
        # 不能用 save_script("conanbuild")——会与 VirtualBuildEnv 的聚合脚本
        # conanbuild.sh 同名冲突导致递归 source 死循环，用独立名。
        build_env.vars(self).save_script("conanbuild_ohos_env")

        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        self._write_gio_unix_pc()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # OHOS 平台适配开关
        tc.variables["ENABLE_WERROR"] = "OFF"
        tc.variables["SKIP_PO"] = "ON"                  # OHOS 无 intltool 可执行
        # GSettings 模块安装 schema 到 ${CMAKE_INSTALL_PREFIX}/share/glib-2.0/schemas/
        tc.variables["GSETTINGS_LOCALINSTALL"] = "ON"
        # cmake-extras 模块目录（share/cmake/GSettings 等）
        cmake_extras = self.dependencies["cmake-extras"].package_folder
        if cmake_extras:
            tc.variables["CMAKE_PREFIX_PATH"] = cmake_extras
        tc.generate()

    def _augment_glib_pkg_config(self):
        """glib proxy-libintl：glib-2.0.pc 等未列出 -lintl，而 src/*.c 包含
        <glib/gi18n.h> 产生 g_libintl_* 符号，链接需 -lintl（libintl.so 由
        glib 包自带）。"""
        for pc_name in ("glib-2.0.pc", "gio-2.0.pc", "gobject-2.0.pc",
                        "gmodule-2.0.pc", "gthread-2.0.pc"):
            pc_file = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc_file):
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            libs_line = next(
                (line for line in content.splitlines() if line.startswith("Libs:")),
                None,
            )
            if libs_line is None or "-lintl" in libs_line.split():
                continue
            content = content.replace(libs_line, libs_line + " -lintl", 1)
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _write_gio_unix_pc(self):
        """glib 配方未导出 gio-unix-2.0.pc，而顶层 CMakeLists 的
        pkg_check_modules 要求 gio-unix-2.0 → 从 glib 包目录合成。"""
        glib = self.dependencies["glib"]
        prefix = glib.package_folder
        content = (
            f"prefix={prefix}\n"
            f"libdir=${{prefix}}/lib\n"
            f"includedir=${{prefix}}/include\n"
            f"includedir1=${{prefix}}/include/gio-unix-2.0\n"
            "\n"
            "Name: GIO unix specific APIs\n"
            "Description: unix specific headers for glib I/O library\n"
            f"Version: {glib.ref.version}\n"
            "Requires: gobject-2.0 gio-2.0\n"
            f'Libs: -L"${{libdir}}"\n'
            f'Cflags: -I"${{includedir}}" -I"${{includedir1}}"\n'
        )
        with open(os.path.join(self.generators_folder, "gio-unix-2.0.pc"), "w",
                  encoding="utf-8") as handle:
            handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 产物为服务可执行文件（安装于 libexec/ayatana-indicator-notifications/），
        # 非头文件库，无需 cpp_info.libs。
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
