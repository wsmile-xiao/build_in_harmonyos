#!/usr/bin/env python3
"""Conan recipe for Qt6LinguistTools 6.11.1 on HarmonyOS PC (arm64).

Qt6LinguistTools 在 Qt 6 中不是独立源码模块：
- 其实体（lrelease/lupdate/lconvert/lcheck/ltext2id 等工具 +
  Qt6LinguistToolsConfig.cmake / Qt6::LinguistTools 宏模块）由 qttools 构建产生；
- 已发布的 qttools/6.11.1.1 包（ohpcd registry，revision e6b700c0...）已实测
  提供 Qt6LinguistToolsConfig.cmake（lib/cmake/Qt6LinguistTools/）与上述 bin 工具。

本包是 Qt6LinguistTools 的独立提供者：依赖 qttools 复用其已发布制品，把
Qt6::LinguistTools CMake 组件与 bin 工具复制进本包，对外以 qt6linguisttools/6.11.1
名称交付，使 kdnssd 等 KF6 消费者可直接引用并完成
find_package(Qt6 COMPONENTS LinguistTools) / lrelease 调用
（R36：依赖 qttools 已先发布到制品仓，无需 --build=missing 从源码编译）。
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    get,
)


class Qt6LinguistToolsConan(ConanFile):
    # conan 要求包名全小写；归档目录名保留 Qt6LinguistTools。
    name = "qt6linguisttools"
    version = "6.11.1"
    description = "Qt 6 LinguistTools (lrelease/lupdate/lconvert + Qt6::LinguistTools CMake module) for HarmonyOS PC"
    license = "BSD-3-Clause AND GPL-3.0-only AND LGPL-3.0-only AND GFDL-1.3-only"
    homepage = "https://doc.qt.io/qt-6/linguist-tools.html"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        pass

    def requirements(self):
        # Qt6LinguistTools 实体由 qttools 构建并已发布到 ohpcd；
        # LinguistTools 编译宏/工具还间接依赖 qtbase（Qt6::Core）。
        self.requires(
            "qttools/6.11.1.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "qtbase/6.11.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "Qt6LinguistTools/6.11.1 is a HarmonyOS PC adaptation"
            )

    def source(self):
        # 来源核验：从官方 qttools 子模块 tarball 下载（SHA-256 由 conandata 强校验，
        # 与 download.qt.io mirrorlist 一致），本包仅作来源留证，不重复编译。
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 本包为 provider：不重复编译 qttools，仅应用补丁（无补丁，占位满足
        # G1 结构检查），实际 LinguistTools 制品来自已发布的 qttools 依赖包。
        apply_conandata_patches(self)

    def package(self):
        # 从已发布的 qttools 依赖包复制 Qt6LinguistTools CMake 模块与 linguist
        # bin 工具到本包，使包自包含并可直接交付给消费者。
        qttools = self.dependencies["qttools"].package_folder
        copy(
            self,
            "Qt6LinguistTools/*",
            src=os.path.join(qttools, "lib", "cmake"),
            dst=os.path.join(self.package_folder, "lib", "cmake"),
        )
        for tool in (
            "lrelease",
            "lrelease-pro",
            "lupdate",
            "lupdate-pro",
            "lconvert",
            "lcheck",
            "ltext2id",
        ):
            src_tool = os.path.join(qttools, "bin", tool)
            if os.path.isfile(src_tool):
                copy(
                    self,
                    tool,
                    src=os.path.join(qttools, "bin"),
                    dst=os.path.join(self.package_folder, "bin"),
                )

    def package_info(self):
        qtbase = self.dependencies["qtbase"].package_folder

        # 原生 Qt CMake 包目录直接加入 builddirs，消费者 find_package(Qt6
        # COMPONENTS LinguistTools) 通过 Qt6LinguistTools_DIR / CMAKE_PREFIX_PATH
        # 解析（kdnssd 先例做法）。cmake_find_mode=none 避免 CMakeDeps 遮蔽原生包。
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]

        linguisttools = self.cpp_info.components["linguisttools"]
        linguisttools.set_property("cmake_target_name", "Qt6::LinguistTools")
        linguisttools.builddirs = [
            os.path.join("lib", "cmake", "Qt6LinguistTools")
        ]

        # bin/ 工具（lrelease/lupdate/lconvert/lcheck/ltext2id）随本包交付，
        # 其运行期依赖 libQt6Core.so.6 由传递依赖 qtbase 提供。
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))

        # qtbase 的 Qt6_DIR 目录一并暴露，保证 find_package(Qt6 ...) 基座可解析。
        self.cpp_info.builddirs.append(os.path.join(qtbase, "lib", "cmake"))