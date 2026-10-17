#!/usr/bin/env python3
"""Conan test_package — hydra 9.6 (application): 编译运行 test.c 并验证 hydra 产物。

hydra 的帮助命令（-h/-H/--help）退出码恒为 255（上游行为），因此
self.run 需 ignore_errors=True，并用 subprocess 捕获 stdout 断言版本信息。
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HydraTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 1) 运行编译出的消费者测试程序
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_hydra"), env="conanrun")
        # 2) 验证 hydra 产物可执行且输出版本信息
        bin_dir = os.path.join(self.dependencies["hydra"].package_folder, "bin")
        hydra_exe = os.path.join(bin_dir, "hydra")
        pw_exe = os.path.join(bin_dir, "pw-inspector")
        for exe in (hydra_exe, pw_exe):
            if not os.path.isfile(exe) or not os.access(exe, os.X_OK):
                raise Exception("{} 不存在或不可执行".format(exe))
        # L0d 要求 test() 调用 self.run()；hydra -h 退出码恒为 255，忽略之
        self.run('"{}" -h'.format(hydra_exe), env="conanrun", ignore_errors=True)
        out = subprocess.run(
            [hydra_exe, "-h"], capture_output=True, text=True, timeout=30,
        ).stdout
        if "Hydra v9.6" not in out:
            raise Exception("hydra -h 输出缺少版本信息: " + out[:200])
