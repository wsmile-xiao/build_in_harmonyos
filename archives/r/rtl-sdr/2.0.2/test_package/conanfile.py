#!/usr/bin/env python3
"""rtl-sdr 2.0.2 test_package —— 真实消费者（C，只用交付的库 + 公共头）。

① 完整消费者用例（平台 rule12）：test_rtlsdr.c 在进程内用 ELF 符号介入伪造
   一台 VID=0x0bda PID=0x2838 的 RTL2832U 电视棒，跑完「设备枚举 → 机型表
   匹配 → USB 字符串读取 → 序列号反查 → 越界错误路径」整条真实链路。
② 上游测试套件：**不存在**（顶层 CMakeLists 无 enable_testing()/add_test，
   src/ 也无测试目标；rtl_test 是需要真实电视棒的硬件自检程序）——如实声明，
   recipe 的 build() 里改为对 8 个 CLI 做启动冒烟。

本测试的编译与链接真依赖被测包：CI 的 L1e(R34) 会把 lib/、include/ 移走后
重跑 conan test，届时本测试必须编译失败。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class RtlsdrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译 + 链接（原生构建时才会执行）")
        else:
            binary = os.path.join(self.cpp.build.bindirs[0], "test_rtlsdr")
            self.run(binary, env="conanrun")
        # 适配自检（M，非上游用例）：交付形态（库/头/CLI/pkg-config/许可/纯净性）
        layout = os.path.join(self.source_folder, "test_layout.py")
        self.run("%s %s %s" % (sys.executable, layout,
                               self.dependencies["rtl-sdr"].package_folder))
