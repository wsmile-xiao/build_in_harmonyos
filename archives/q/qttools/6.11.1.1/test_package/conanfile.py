#!/usr/bin/env python3
"""CMake consumer test for Qt Tools 6.11.1."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QttoolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # E225: 用 Conan 管理的唯一临时目录作为 test_package 构建根，
        # 避免 CMakeToolchain 把 CMakeUserPresets.json 写回 source。
        cmake_layout(self, build_folder="$TMP")

    def generate(self):
        tc = CMakeToolchain(self)
        # E225: 从生成源头阻止 preset 写回 source（user_presets_path=False）。
        tc.user_presets_path = False
        qtbase = self.dependencies["qtbase"].package_folder
        qttools = self.dependencies["qttools"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        tc.variables["Qt6UiTools_DIR"] = os.path.join(qttools, "lib", "cmake", "Qt6UiTools")
        tc.variables["Qt6LinguistTools_DIR"] = os.path.join(
            qttools, "lib", "cmake", "Qt6LinguistTools"
        )
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise ConanInvalidConfiguration(
                    "qttools test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_package")
            # QUiLoader 加载 QWidget 需 QApplication + 无显示平台（OHOS 无 xcb）。
            self.run(
                "cmake -E env QT_QPA_PLATFORM=offscreen \"{}\"".format(executable),
                env="conanrun",
                ignore_errors=False,
            )
