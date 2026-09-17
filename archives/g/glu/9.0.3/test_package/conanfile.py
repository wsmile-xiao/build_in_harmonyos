#!/usr/bin/env python3
"""Test package for glu 9.0.3 — consumer compile/link + **real execution** verification.

本机即为 HarmonyOS aarch64 设备（非交叉编译宿主），故按 R34 要求**真实执行**
被测二进制，而非仅编译。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class GluTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv 必需：被测程序 NEEDED 里是 soname `libGLU.so.1`（无 RUNPATH），
    # 运行期需靠 conanrun 环境提供库搜索路径。缺该生成器时 conanrun.sh 存在但
    # **不含 LD_LIBRARY_PATH**，实测报：
    #   Error loading shared library libGLU.so.1: (needed by ./test_glu)
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_glu")
        if can_run(self):
            # 真实执行（R34）：调用 gluErrorString 并校验返回值/版本宏
            self.run(exe, env="conanrun")
        else:
            # 目标平台不可执行时退化为二进制存在性检查
            self.output.warning(
                f"cannot run {exe} on this host — falling back to existence check")
            if not os.path.isfile(exe):
                raise ConanException(f"test binary not built: {exe}")
