#!/usr/bin/env python3
"""Conan test_package — libqalculate 5.8.2-r0.

Tests that the libqalculate package can be found, compiled against,
and linked successfully on OpenHarmony (R34: real API usage).

File location: archives/{letter}/libqalculate/{version}/test_package/conanfile.py

libqalculate 的头文件 qalculate.h 直接 #include <gmp.h>/<mpfr.h>/<libxml>
等，因此 test_package 必须显式 requires 这些运行时依赖，CMakeDeps 才会
生成对应 cmake 配置并传递 include 路径（否则 gmp.h not found）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibqalculateTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 传递依赖需要头文件（qalculate.h -> gmp.h/mpfr.h/libxml2）显式声明
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")
        self.requires("libxml2/2.15.3")
        self.requires("readline/8.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # E092 fix: CMake does not recognise HarmonyOS as a target platform.
        # Force CMAKE_SYSTEM_NAME=Linux so CMake uses the standard Linux
        # platform module instead of aborting on "unknown system".
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 运行时注入 SDK libc++ 目录 + conan 依赖 lib 目录：test 二进制与
        # libqalculate.so 是 SDK clang 编译的，依赖新版本 libc++_shared.so；
        # 若不加 LD_LIBRARY_PATH，musl 加载器会命中系统 /system/lib64 的旧版
        # libc++_shared.so（符号集不匹配 -> Error relocating: symbol not found）。
        # （libgsf os.environ 直接注入模式，conanrun 沙箱 buildenv 不生效）
        sdk_cxx = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                   "ohos/native/llvm/lib/aarch64-linux-ohos")
        _lib_dirs = [d for d in [sdk_cxx, "/system/lib64", "/system/lib"]
                     if os.path.isdir(d)]
        for _ref, _dep in self.dependencies.items():
            for _lp in (_dep.cpp_info.libdirs or []):
                if os.path.isabs(_lp) and _lp not in _lib_dirs:
                    _lib_dirs.append(_lp)
        _prev = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            list(dict.fromkeys(_lib_dirs + ([_prev] if _prev else []))))
        self.output.info("LD_LIBRARY_PATH=" + os.environ["LD_LIBRARY_PATH"])
        # R34/CI L0d/L1d: test() 必须调用被测包的二进制/API（禁止假测试）
        cmake = CMake(self)
        cmake.test()
        _bin = os.path.join(self.cpp.build.bindirs[0], "test_libqalculate")
        self.run(f'"{_bin}"')