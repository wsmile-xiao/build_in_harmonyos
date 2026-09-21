#!/usr/bin/env python3
"""Consumer test for kcolorpicker (kColorPicker-Qt6) on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KColorPickerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # qtbase cmake_find_mode=none：Qt6 config 指向 qtbase 包内目录；
        # kColorPicker-Qt6_DIR 指向被测包自身导出的 CMake config，
        # 模拟下游 kImageAnnotator 0.7.2 的真实消费方式：
        #   find_package(kColorPicker-Qt6 0.3.1 REQUIRED)
        #   target_link_libraries(... PRIVATE kColorPicker::kColorPicker)
        qtbase_prefix = self.dependencies["qtbase"].package_folder
        kcp_prefix = self.dependencies["kcolorpicker"].package_folder
        tc.cache_variables["Qt6_DIR"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6")
        tc.cache_variables["Qt6Widgets_DIR"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6Widgets")
        tc.cache_variables["kColorPicker-Qt6_DIR"] = os.path.join(
            kcp_prefix, "lib", "cmake", "kColorPicker-Qt6")
        # 运行期闭包说明（E135）：CMake 无 HarmonyOS 平台模块，链接行无
        # -rpath，设备默认路径无 Qt 库——test() 用 env="conanrun" 运行
        # （Conan 自动把依赖 cpp_info.libdirs 写入 conanrun 的 LD_LIBRARY_PATH，
        # karchive/6.19.0 同机先例），解析 libQt6*.so.6 与包内 libkColorPicker.so
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # -j1：OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败（opensp 先例）
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise ConanInvalidConfiguration(
                    "kcolorpicker test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_kcolorpicker")
            self.run(f'"{executable}"', env="conanrun", ignore_errors=False)
