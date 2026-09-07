#!/usr/bin/env python3
"""Conan recipe — earcut 3.2.3 (mapbox/earcut.hpp, header-only C++ polygon triangulation).

earcut.hpp 是 mapbox 的单文件 header-only 多边形三角剖分库（earcut.js 的 C++ 移植版）。
- header-only：仅提供 include/mapbox/earcut.hpp 一个头文件，无任何第三方运行时依赖
- 上游 CMake：INTERFACE 库 earcut_hpp，安装 include/mapbox + earcut_hpp-config.cmake
- HarmonyOS 适配：无需源码改动；R32 平台判断用 in ("Linux","OHOS")；
  构建/测试默认关闭（上游测试依赖 FetchContent 拉取 earcut.js fixtures/googletest，
  由 CI 独立跑上游测试，配方内以 test_package 消费者验证为准）
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class EarcutConan(ConanFile):
    name = "earcut"
    version = "3.2.3"
    description = "Fast, header-only polygon triangulation (earcut.js C++ port) by Mapbox"
    license = "ISC"
    homepage = "https://github.com/mapbox/earcut.hpp"
    url = ""  # CI fills this
    topics = ("triangulation", "polygon", "geometry", "header-only", "earcut")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 库本身是 INTERFACE 目标，无需编译；关闭上游测试/基准/可视化（依赖 FetchContent 网络拉取）
        tc.variables["EARCUT_BUILD_TESTS"] = False
        tc.variables["EARCUT_BUILD_BENCH"] = False
        tc.variables["EARCUT_BUILD_VIZ"] = False
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
        self.cpp_info.set_property("cmake_file_name", "earcut_hpp")
        self.cpp_info.set_property("cmake_target_name", "earcut_hpp::earcut_hpp")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
