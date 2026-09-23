#!/usr/bin/env python3
"""Conan recipe for kapow 1.7.0 (CMake, Qt6 punch-clock GUI) on HarmonyOS PC.

kapow 是纯可执行包（Qt6 Widgets GUI，无 lib/ 产物）。OHOS 适配裁剪：
- PrintSupport（制品仓 qtbase FEATURE_printsupport=OFF）：移除打印功能，
  保留 HTML/iCalendar/CSV 导出（patches/0001~0003）。
- TranslateMetainfo 的 Gettext(msgfmt) 硬依赖：CI clean 环境无 gettext，
  移除 desktop/appdata 元数据处理（patches/0001）。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KapowConan(ConanFile):
    name = "kapow"
    version = "1.7.0"
    description = "kapow 1.7.0 punch clock to track time spent on projects"
    license = "GPL-3.0-or-later"
    homepage = "https://gottcode.org/kapow/"
    url = "https://gottcode.org/kapow/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 组件面：Core/Gui/Network/Widgets/Test 由 qtbase 提供，
        # LinguistTools（lrelease，qt_add_translations 用）由 qttools 提供。
        self.requires("qtbase/6.11.1")
        self.requires("qttools/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "ON"
        tc.variables["WARNINGS_ARE_ERRORS"] = "OFF"
        # 启用上游单元测试（tests/，Qt6::Core+Qt6::Test；qtbase 包内含
        # libQt6Test 与 Qt6TestConfig.cmake，offscreen 可运行）
        tc.variables["ENABLE_TESTS"] = "ON"
        # 各 Qt6 包前缀：qtbase 提供 Qt6Config，qttools 提供 Qt6LinguistTools
        qtbase = self.dependencies["qtbase"].package_folder
        qttools = self.dependencies["qttools"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(
            p.replace("\\", "/") for p in (qtbase, qttools)
        )
        # Qt6Config 的组件搜索受 PATHS 限定在 qtbase 前缀，需显式给出
        # LinguistTools(qttools) 组件目录（bambootracker 先例）
        tc.cache_variables["Qt6LinguistTools_DIR"] = (
            f"{qttools}/lib/cmake/Qt6LinguistTools"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Qt6 工具(lrelease 等)与测试可执行文件运行期需要 qtbase 动态库，
        # 显式供给其 lib 目录
        env = Environment()
        env.append_path(
            "LD_LIBRARY_PATH",
            str(self.dependencies["qtbase"].package_folder) + "/lib",
        )
        with env.vars(self).apply():
            cmake.build()
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # kapow 是纯可执行包（GUI/Qt6），无 lib/ 产物，不声明库。
        # 声明不存在的 lib 会让 CMakeDeps 生成指向缺失库的 target，
        # 导致 test_package find_package 报 "Library not found"（G2 E225）。
        pass
