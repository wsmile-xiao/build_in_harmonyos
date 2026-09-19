#!/usr/bin/env python3
"""Conan test_package — zmusic 1.3.0 consumer test.

Consumer 视角: find_package(zmusic) + ZMusic::zmusic，端到端验证 C API：
配置枚举 → 内存 MOD 解码（内置 DUMB）→ 启动播放 → PCM 渲染（非零音频）
→ MIDI 类型识别。上游无 tests/ 目录，故本测试即鸿蒙特有测试。
"""
import os
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

# 同主配方：HMDFS 上偶发的静默构建失败，重试即可收敛
BUILD_RETRIES = 3


class ZmusicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = arch_map.get(
                str(self.settings.arch), str(self.settings.arch)
            )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # 单文件编译，串行即可；避免 conan 默认 "-j<核数>" 的资源竞争
        cmd = f'cmake --build "{self.build_folder}"'
        for attempt in range(1, BUILD_RETRIES + 1):
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                  cwd=self.build_folder, env=os.environ)
            if proc.returncode == 0:
                if proc.stdout:
                    self.output.info(proc.stdout[-2000:])
                break
            tail = (proc.stdout or "") + (proc.stderr or "")
            self.output.warning(
                f"测试程序构建第 {attempt}/{BUILD_RETRIES} 次失败（rc={proc.returncode}），"
                f"输出尾部:\n{tail[-2000:]}"
            )
            if attempt == BUILD_RETRIES:
                raise ConanException(
                    f"test_package 构建连续 {BUILD_RETRIES} 次失败，尾部输出:\n{tail[-4000:]}"
                )
            time.sleep(5)

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_zmusic")
        if cross_building(self):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run the OHOS test package"
                )
            self.run(f'"{qemu}" "{bin_path}"', env="conanrun")
        else:
            self.run(bin_path, env="conanrun")
