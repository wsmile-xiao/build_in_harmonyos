#!/usr/bin/env python3
"""Conan recipe — ayatana-indicator-display 26.6.0.

Ayatana System Indicator — Display：显示菜单系统指示器服务
（brightness / colour temperature 控制，MATE/Lomiri 桌面使用）。

OHOS 适配说明：
  - 依赖 libayatana-common >= 0.9.3、gio-unix-2.0/glib-2.0、properties-cpp
    （顶层 CMakeLists 的 pkg_check_modules SERVICE_DEPS REQUIRED），通过
    PkgConfigDeps 生成 .pc（CMakeToolchain 自动把 generators 目录注入
    PKG_CONFIG_PATH）。
  - glib 配方 cpp_info 未声明 gio-unix-2.0 组件，PkgConfigDeps 不会生成
    转发 gio-unix-2.0.pc；_augment_glib_unix_pkg_config() 从 glib 包内
    复制该 .pc 并改写 prefix（与 ayatana-ido 的 _augment_glib_pkg_config
    同法）。
  - 0001-skip-data-po-subdirs.patch：data/CMakeLists.txt 用
    find_package(GSettings REQUIRED)+add_schema、po/CMakeLists.txt 用
    find_package(Intltool REQUIRED)，OHOS 均无这些 CMake 模块，SKIP_DATA_PO=ON
    跳过 data/ 与 po/ 子目录（与 libayatana-common 同法）。
  - ENABLE_COLOR_TEMP/ENABLE_RDA=OFF：colour temperature / RDA 分支依赖
    libgeoclue-2.0/accountsservice/x11/xrandr/rda，OHOS 无这些桌面库，关闭后
    service.cpp 的彩色温控逻辑不编译（产品核心亮度控制不受影响）。
  - 产物：libayatana-indicator-display.a（STATIC）+ 可执行
    ayatana-indicator-display-service（安装到 libexec/ayatana-indicator-display）。
  - 上游 tests/ 依赖 Qt5Test/Qt5DBus/libqtdbtest-1/libqtdbusmock-1/GMock，
    OHOS 不可用，ENABLE_TESTS=OFF。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class AyatanaindicatordisplayConan(ConanFile):
    name = "ayatana-indicator-display"
    version = "26.6.0"
    description = "Ayatana System Indicator — Display：显示菜单系统指示器服务（亮度/色温控制）"
    license = "GPL-3.0"
    homepage = "https://github.com/AyatanaIndicators/ayatana-indicator-display"
    url = "https://github.com/AyatanaIndicators/ayatana-indicator-display"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 顶层 CMakeLists pkg_check_modules(SERVICE_DEPS REQUIRED libayatana-common gio-unix-2.0 glib-2.0 properties-cpp)
        self.requires("libayatana-common/0.9.13", transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.88.0.1", transitive_headers=True, transitive_libs=True)
        # header-only 属性/信号库
        self.requires("properties-cpp/0.0.4", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_unix_pkg_config()
        tc = CMakeToolchain(self)
        # OHOS: 无 GSettings/Intltool CMake 模块，跳过 data/ po/ 子目录
        tc.variables["SKIP_DATA_PO"] = "ON"
        # 关闭 colour temperature / RDA（依赖 libgeoclue/accountsservice/x11/xrandr/rda，OHOS 无）
        tc.variables["ENABLE_COLOR_TEMP"] = "OFF"
        tc.variables["ENABLE_RDA"] = "OFF"
        # 上游测试依赖 Qt5Test/Qt5DBus/libqtdbtest-1/libqtdbusmock-1/GMock，OHOS 不可用，关闭
        tc.variables["ENABLE_TESTS"] = "OFF"
        tc.variables["ENABLE_WERROR"] = "OFF"
        tc.generate()

    def _augment_glib_unix_pkg_config(self):
        # glib 配方 cpp_info 未声明 gio-unix-2.0 组件，PkgConfigDeps 不生成
        # 转发 gio-unix-2.0.pc（顶层 pkg_check_modules SERVICE_DEPS REQUIRED
        # 需要它）。从 glib 包内复制该 .pc 到 generators 目录并改写 prefix，
        # 使其 Cflags 指向 glib 包内头文件（与 ayatana-ido 同法）。
        glib_folder = self.dependencies["glib"].package_folder
        src = os.path.join(glib_folder, "lib", "pkgconfig", "gio-unix-2.0.pc")
        if not os.path.isfile(src):
            return
        dst = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        prefix = glib_folder.replace(os.sep, "/")
        content = open(src, encoding="utf-8").read()
        content = content.replace("prefix=/", f"prefix={prefix}")
        open(dst, "w", encoding="utf-8", newline="\n").write(content)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 产物为 service 可执行文件，cmake install 实际落到
        # ${prefix}/bin/ayatana-indicator-display/（GNUInstallDirs 在
        # OHOS 未知系统上 LIBEXECDIR 取默认 bin）。
        self.cpp_info.bindirs = ["bin/ayatana-indicator-display"]
