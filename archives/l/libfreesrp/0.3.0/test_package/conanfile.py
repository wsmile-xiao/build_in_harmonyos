#!/usr/bin/env python3
"""Conan test_package — libfreesrp 0.3.0 consumer smoke test (L1).

上游无自动化测试（CMakeLists.txt 无 ctest/add_test，无 tests/ 目录），
验证完全由本消费者测试承担：链接 libfreesrp.so，走 libusb 初始化+枚举路径。
"""
import os
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout

BUILD_RETRIES = 3


class LibfreesrpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # 同主配方：CMake helper 在本机 OHOS 的 capture_output 管道下会静默
        # 失败（无 error: 诊断），subprocess.run + 显式 env 继承稳定通过。
        cmake = CMake(self)
        cmake.configure()
        build_env = os.environ.copy()
        for attempt in range(1, BUILD_RETRIES + 1):
            proc = subprocess.run('cmake --build "%s"' % self.build_folder,
                                  shell=True, capture_output=True, text=True,
                                  cwd=self.build_folder, env=build_env)
            if proc.returncode == 0:
                break
            tail = (proc.stdout or "") + (proc.stderr or "")
            if "error:" in tail:
                raise ConanException(
                    "cmake --build 报出编译器错误（非环境性静默失败），尾部输出:\n%s"
                    % tail[-4000:]
                )
            if attempt == BUILD_RETRIES:
                raise ConanException(
                    "cmake --build 连续 %d 次失败且始终无 error: 输出，尾部输出:\n%s"
                    % (BUILD_RETRIES, tail[-4000:])
                )
            time.sleep(5)

    def test(self):
        binpath = os.path.join(self.cpp.build.bindirs[0], "test_freesrp")
        self.run('"%s"' % binpath, env="conanrun")
