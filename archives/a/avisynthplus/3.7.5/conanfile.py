#!/usr/bin/env python3
"""Conan recipe for avisynthplus 3.7.5 — AviSynth+ video processing framework.

AviSynth+ 是 C++ 视频处理/帧服务框架（GPL-2.0+），CMake 构建。核心库
libavisynth（AvsCore）仅依赖 pthread（系统库）；CUDA/Intel SIMD/默认插件
均为可选（默认关闭，插件非核心）。

OHOS 适配:
- CMake 标准交叉编译，无需源码 patch（预期路径 A）；
- 关闭可选：ENABLE_CUDA=OFF、ENABLE_INTEL_SIMD=OFF、ENABLE_PLUGINS=OFF；
- 测试: test_package 用 avisynth.h 头 + GetVersion 验证库可用。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps
from conan.tools.files import get


class AvisynthplusConan(ConanFile):
    name = "avisynthplus"
    version = "3.7.5"
    description = "AviSynth+ - improved version of AviSynth (video processing)"
    license = "GPL-2.0-or-later"
    homepage = "http://avs-plus.net/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 可选功能关闭（CUDA/Intel SIMD 仅 x86 相关；插件非核心库）
        tc.variables["ENABLE_CUDA"] = "OFF"
        tc.variables["ENABLE_INTEL_SIMD"] = "OFF"
        tc.variables["ENABLE_PLUGINS"] = "OFF"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        # CI 沙箱中 lld 加载 libxml2.so.16 失败（symbol not found）→
        # CMake 编译器检测 broken：CI 注入的 LD_LIBRARY_PATH（ci_o
        # lib/external 空壳库）优先级高于 lld 的 RUNPATH（$ORIGIN/../lib，
        # 即 SDK llvm/lib 的完整 libxml2.so.16）。修复：将 clang 所在 SDK 的
        # llvm/lib（含完整 libxml2.so.16）前置注入 LD_LIBRARY_PATH。
        cc = self.conf.get("tools.build:compiler_executables", default={}).get(
            "c") or "clang"
        import os as _os
        _clang_real = _os.path.realpath(cc)
        _llvm_lib = _os.path.join(
            _os.path.dirname(_os.path.dirname(_clang_real)), "lib")
        if _os.path.isdir(_llvm_lib):
            _old = _os.environ.get("LD_LIBRARY_PATH", "")
            _os.environ["LD_LIBRARY_PATH"] = (
                _llvm_lib + (_os.pathsep + _old if _old else ""))
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["avisynth"]
        self.cpp_info.set_property("cmake_file_name", "avisynth")
        self.cpp_info.set_property("cmake_target_name", "avisynth::avisynth")
