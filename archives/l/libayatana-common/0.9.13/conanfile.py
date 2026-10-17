#!/usr/bin/env python3
"""Conan recipe — libayatana-common 0.9.13.

Ayatana Indicators 公共库：桌面会话检测（lomiri/unity/gnome/mate/xfce/
pantheon/budgie）、命令执行、zenity 交互等通用工具函数。

OHOS 适配说明：
  - glib 依赖：通过 PkgConfigDeps 生成 glib-2.0.pc / gio-2.0.pc，供顶层
    CMakeLists 的 pkg_check_modules(DEPS REQUIRED glib-2.0 gio-2.0) 使用
    （CMakeToolchain 自动把 generators 目录注入 PKG_CONFIG_PATH）。
  - 0001-skip-data-po-subdirs.patch：OHOS 无 GSettings/Intltool CMake
    模块（data/CMakeLists.txt find_package(GSettings REQUIRED)、
    po/CMakeLists.txt find_package(Intltool REQUIRED) 均会失败），
    SKIP_DATA_PO=ON 跳过 data/ 与 po/ 子目录。
  - CMake 目标名 ayatana-common -> 产物 lib/libayatana-common.so，
    cpp_info.libs 用去掉 lib 前缀的名称。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class LibayatanacommonConan(ConanFile):
    name = "libayatana-common"
    version = "0.9.13"
    description = "Ayatana Indicators 公共库：桌面会话检测、命令执行、zenity 交互等通用工具函数"
    license = "GPL-3.0"
    homepage = "https://github.com/AyatanaIndicators/libayatana-common"
    url = "https://github.com/AyatanaIndicators/libayatana-common"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # 上游 src/CMakeLists.txt 硬编码 add_library(ayatana-common SHARED ...)，
    # 产物必然是共享库（非系统同名库，允许动态）；shared=True 让 conanrun
    # 环境注入包 lib 目录（否则 test_package 运行时找不到 libayatana-common.so）。
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # utils.h 直接包含 glib.h / glib-object.h / gio/gio.h，需透传头文件与库
        self.requires("glib/2.88.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # OHOS: 无 GSettings/Intltool CMake 模块，跳过 data/ po/ 子目录
        tc.variables["SKIP_DATA_PO"] = "ON"
        # 上游测试需要 GMock/Vala/GObjectIntrospection，OHOS 不可用，关闭
        tc.variables["ENABLE_TESTS"] = "OFF"
        tc.variables["ENABLE_WERROR"] = "OFF"
        tc.variables["ENABLE_LOMIRI_FEATURES"] = "OFF"
        # L5 SONAME 门禁由 0002-soname-link-flag.patch 修复（target 级 LINK_FLAGS，
        # 不干扰 toolchain 的 -L 路径；conan_toolchain 的 CONAN_* 变量注入存在
        # 定义时序问题，实测不生效）。
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # src/CMakeLists.txt 目标名 ayatana-common -> 产物 lib/libayatana-common.so
        self.cpp_info.libs = ["ayatana-common"]
        # utils.h 包含 glib.h/glib-object.h/gio/gio.h，透传 glib 依赖
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gobject-2.0", "glib::gio-2.0"]
