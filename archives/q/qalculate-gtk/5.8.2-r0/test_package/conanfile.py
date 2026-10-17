#!/usr/bin/env python3
"""Conan test_package — qalculate-gtk 5.8.2-r0.

qalculate-gtk 为 GTK3 GUI 应用（无头系统无法启动 GUI），故测试其核心依赖
libqalculate 的计算链：include 头文件 + 链接库 + 实质执行算术计算（R34）。

File location: archives/q/qalculate-gtk/{version}/test_package/conanfile.py

注：qalculate-gtk 头文件 qalculate.h 直接依赖 gmp/mpfr/libxml2 等，
test_package 显式 requires 使 CMakeDeps 传递 include 路径。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QalculateGtkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 传递依赖头文件（qalculate.h -> gmp.h/mpfr.h/libxml2）
        self.requires("libqalculate/5.8.2-r0")
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")
        self.requires("libxml2/2.15.3")
        self.requires("readline/8.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # E092 fix: CMake does not recognise HarmonyOS as a target platform.
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 运行时注入 SDK libc++ + conan 依赖 lib 目录（libgsf os.environ 模式）
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
        # R34/CI L0d/L1d: 必须 self.run 实际执行被测二进制（禁止假测试）
        cmake = CMake(self)
        cmake.test()
        _bin = os.path.join(self.cpp.build.bindirs[0], "test_qalculate_gtk")
        self.run(f'"{_bin}"')