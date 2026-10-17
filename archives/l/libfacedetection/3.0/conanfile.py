#!/usr/bin/env python3
"""Conan recipe — libfacedetection 3.0 (CNN-based face detection library).

Upstream: https://github.com/ShiqiYu/libfacedetection  (tag v3.0, BSD-3-Clause)
构建系统：CMake（顶层 CMakeLists.txt，无第三方运行时依赖）。
产物：libfacedetection.{a,so} + include/facedetection/*.h + cmake 配置。

平台说明（HarmonyOS PC, aarch64）：
- 目标 arch=armv8 时启用 ENABLE_NEON（上游 ARM SIMD 加速）；x86 保持 AVX2/AVX512 关闭。
- 上游 cmake_minimum_required(2.8.12) 与 CMake>=4 不兼容，通过
  CMAKE_POLICY_VERSION_MINIMUM=3.5 保持兼容（本地与 CI 同源，不改源码）。
- DEMO=OFF：example 需要 OpenCV，不是库依赖，不进入配方构建。
- USE_OPENMP=OFF：避免引入 OpenMP 运行时依赖（上游可选）。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibfacedetectionConan(ConanFile):
    name = "libfacedetection"
    version = "3.0"
    description = "An open source library for CNN-based face detection in images (1000FPS+ level)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ShiqiYu/libfacedetection"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游无第三方运行时依赖（模型已静态内嵌于 facedetectcnn-data.cpp）
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake>=4 已移除 <3.5 兼容；上游 min=2.8.12 → 用策略最小版本兼容
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 目标平台为 aarch64：启用 NEON SIMD；x86 关闭 AVX2/AVX512（避免误配）
        tc.variables["ENABLE_NEON"] = "ON" if str(self.settings.arch).startswith("arm") else "OFF"
        tc.variables["ENABLE_AVX2"] = "OFF"
        tc.variables["ENABLE_AVX512"] = "OFF"
        # DEMO 需要 OpenCV，非库依赖；OpenMP 可选，避免额外运行时
        tc.variables["DEMO"] = "OFF"
        tc.variables["USE_OPENMP"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["facedetection"]
        self.cpp_info.set_property("cmake_file_name", "facedetection")
        self.cpp_info.set_property("cmake_target_name", "facedetection")
        # 头文件安装在 include/facedetection/（上游 PUBLIC_HEADER 约定）
        self.cpp_info.includedirs = ["include"]
