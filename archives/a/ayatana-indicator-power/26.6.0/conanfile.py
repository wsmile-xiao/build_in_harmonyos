#!/usr/bin/env python3
"""Conan recipe — ayatana-indicator-power 26.6.0 (CMake).

Ayatana 电源指示器服务：D-Bus session service，负责电池/亮度等电源
状态监听与桌面通知，会话内由 ayatana-indicator 框架加载。

HarmonyOS PC 适配说明：
  - 构建系统为 CMake（非 autotools），顶层 CMakeLists.txt 通过
    pkg_check_modules(SERVICE_DEPS REQUIRED glib-2.0 gio-2.0 gio-unix-2.0
    libayatana-common) 解析依赖。
  - PkgConfigDeps 生成各依赖 .pc 后需两个补充：
    * glib 配方只提供 glib-2.0/gio-2.0/gobject-2.0 等 .pc，缺 gio-unix-2.0.pc
      → 从 glib 包目录合成（参考 gtk+ 配方 _write_gio_unix_pc 模式）。
    * glib 的 proxy-libintl 提供 g_libintl_* 符号，glib-2.0.pc 未列 -lintl
      → 追加 -lintl（与 libayatana-common 配方 _augment_glib_pkg_config 一致）。
  - 系统同名库（glib/libayatana-common）均为共享库由 conan 依赖
    链管理，无需静态化（R26 仅要求不得将同名 .so 输出到系统路径）。
  - OHOS 无 intltool 可执行 → 0001 补丁新增 SKIP_PO 选项跳过 po/ 子目录。
  - data/CMakeLists.txt 原 XDG_AUTOSTART_DIR=/etc/xdg/autostart 为绝对路径，
    会写出 package 目录之外 → 补丁改为 ${CMAKE_INSTALL_PREFIX}/etc/xdg/autostart。
  - main.c 增加 --version/--help 支持：D-Bus 服务在 OHOS PC 无 session bus，
    原始程序会进入 g_main_loop 阻塞；加参数处理使服务可被 smoke test 验证
    （test_package 以 conanrun 环境运行）。
  - RDA（远程桌面感知，rda/librda）在 OHOS 无对应服务且 librda 未发布到
    制品仓 → ENABLE_RDA=OFF 关闭该可选特性（R36 记录）。
  - libnotify 整体禁用（0004 补丁，DISABLE_NOTIFY）：OHOS 无 D-Bus 通知
    守护进程，通知功能本就无法工作；且 libnotify 的 gdk-pixbuf 依赖链与
    libayatana-common 各自内嵌导出整套静态 glib 2.88，同进程加载时符号
    互操作共用注册表，导致 test_package 冒烟测试启动即崩溃
    （cannot register existing type 'gchar'，SIGABRT）。去除后运行链仅剩
    单一 glib 提供者（libayatana-common），进程稳定。
  - cmake-extras 提供 GSettings CMake 模块（find_package(GSettings)），
    作为构建期依赖引入，其包目录注入 CMAKE_PREFIX_PATH。
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


class AyatanaindicatorpowerConan(ConanFile):
    name = "ayatana-indicator-power"
    version = "26.6.0"
    description = "Ayatana indicator power service — D-Bus battery/backlight session service"
    license = "GPL-3.0"
    homepage = "https://github.com/AyatanaIndicators/ayatana-indicator-power"
    url = "https://github.com/AyatanaIndicators/ayatana-indicator-power"

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
        # libnotify 不引入（0004 补丁 DISABLE_NOTIFY）：见文件头适配说明——
        # OHOS 无通知守护进程，且其 gdk-pixbuf 依赖链与 libayatana-common
        # 双 glib 符号互操作导致进程启动崩溃。
        # cmake-extras 提供 GSettings/Intltool CMake 模块（无原生编译，纯数据包）
        self.requires("cmake-extras/1.9")

    def build_requirements(self):
        # gettext 提供 msgmerge/msgfmt：GSettingsConfig.cmake 强制 find_package(Gettext
        # REQUIRED)（FindGettext 需 GETTEXT_MSGMERGE_EXECUTABLE），OHOS 系统无该工具，
        # CI 干净环境因此失败；gettext/0.22.5.1 为已合并的 application 工具包，
        # conan 会将其中 bin/ 注入 CMAKE_PROGRAM_PATH（FindGettext 按此查找）。
        # 与 ayatana-indicator-notifications/23.10.1 配方同源解法。
        self.tool_requires("gettext/0.22.5.1")
        # gdbus-codegen：上游 src/CMakeLists.txt 的 GdbusCodegen.cmake 用
        # find_program(GDBUS_CODEGEN gdbus-codegen) 定位，生成 D-Bus 接口代码。
        # OHOS 系统 /data/service/hnp/bin/gdbus-codegen 是指向缺失目标的悬空
        # 符号链接（glib.org/glib_2.38.2 未随 CI worker 提供），不可用。glib 包
        # 自带可用的 gdbus-codegen，tool_require 使 CMakeToolchain 将其 bin/ 注入
        # CMAKE_PROGRAM_PATH——find_program 优先于 PATH 搜索该路径，从而稳定命中。
        self.tool_requires("glib/2.88.0.1")

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
        # 注意：不能用 save_script("conanbuild")——会与 VirtualBuildEnv 的
        # 聚合脚本 conanbuild.sh 同名冲突导致自身递归 source 死循环。
        # 用独立名 conanbuild_ohos_env，VirtualBuildEnv 会自动聚合它。
        build_env.vars(self).save_script("conanbuild_ohos_env")

        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        self._write_gio_unix_pc()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # OHOS 平台适配开关
        tc.variables["ENABLE_TESTS"] = "OFF"          # 上游测试需 GMock/dbustest，OHOS 不可用
        tc.variables["ENABLE_WERROR"] = "OFF"
        tc.variables["ENABLE_LOMIRI_FEATURES"] = "OFF"  # lomiri-schemas/sounds 未适配
        tc.variables["ENABLE_DEVICEINFO"] = "OFF"       # deviceinfo 未适配
        tc.variables["ENABLE_RDA"] = "OFF"              # librda 未发布到制品仓 (R36)
        tc.variables["SKIP_PO"] = "ON"                  # OHOS 无 intltool 可执行
        # R37: 主程序静态链接了部分 glib 对象（GMenu/GBinding/GDBus-export 等，
        # libayatana-common 的嵌入 glib 未导出这些符号）。若不隐藏，这些符号会与
        # libayatana-common.so 内嵌并导出的 glib 符号发生 ELF 符号互操作，
        # 导致 glib 类型系统被初始化两次 → 运行 --version 即 SIGABRT
        # "cannot register existing type 'gchar'"。用 --exclude-libs 把静态
        # glib 符号改为局部符号，进程内只保留一份有效的 glib 类型注册表。
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--exclude-libs,ALL"
        # GSettings 模块安装 schema 到 ${CMAKE_INSTALL_PREFIX}/share/glib-2.0/schemas/
        tc.variables["GSETTINGS_LOCALINSTALL"] = "ON"
        # cmake-extras 模块目录（share/cmake/GSettings 等）
        cmake_extras = self.dependencies["cmake-extras"].package_folder
        if cmake_extras:
            tc.variables["CMAKE_PREFIX_PATH"] = cmake_extras
        tc.generate()

    def _augment_glib_pkg_config(self):
        """glib proxy-libintl：glib-2.0.pc 等未列出 -lintl，而 utils/notifier
        等源文件包含 <glib/gi18n.h> 产生 g_libintl_* 符号，链接需 -lintl
        （libintl.so 由 glib 包自带）。"""
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
        pkg_check_modules 要求 gio-unix-2.0 → 从 glib 包目录合成。
        Version 从 glib 依赖 ref 动态取值，避免随 glib 升版不同步。"""
        glib = self.dependencies["glib"]
        prefix = glib.package_folder
        version = glib.ref.version
        content = (
            f"prefix={prefix}\n"
            f"libdir=${{prefix}}/lib\n"
            f"includedir=${{prefix}}/include\n"
            f"includedir1=${{prefix}}/include/gio-unix-2.0\n"
            "\n"
            "Name: GIO unix specific APIs\n"
            "Description: unix specific headers for glib I/O library\n"
            f"Version: {version}\n"
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
        # 产物为服务可执行文件（安装于 libexec/ayatana-indicator-power/），
        # 非头文件库，无需 cpp_info.libs。
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
