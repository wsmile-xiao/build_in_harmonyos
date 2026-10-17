#!/usr/bin/env python3
"""Test package for cute_tiled 1.0.0 (single-header C library, bootstrap skeleton)."""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy


class CuteTiledTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # E225: Conan 2 标准 conan create 下用 $TMP 让 Conan 管理唯一临时构建目录
        cmake_layout(self, build_folder="$TMP")

    def generate(self):
        tc = CMakeToolchain(self)
        # E225: 禁止 CMakeToolchain 向 source 写 CMakeUserPresets.json，零污染
        tc.user_presets_path = False
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        # 直接以绝对路径传入样例地图 JSON，规避 CWD 依赖
        exe = os.path.join(self.cpp.build.bindirs[0], "test_cute_tiled")
        json_path = os.path.join(self.source_folder, "test_map.json")
        self.run('"{}" "{}"'.format(exe, json_path), env="conanrun")
