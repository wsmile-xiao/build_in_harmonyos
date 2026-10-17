#!/usr/bin/env python3
"""libnvmemi 1.16.2 test_package —— 真实消费者（C，仅用交付的库 + 公共头）。

① 完整消费者用例（平台 rule12）：test_libnvme_mi.c 在进程内用 ELF 符号介入
   伪造一个 MCTP 设备，跑完整条 NVMe-MI 业务流程：建立端点 → MI Control
   Primitive 枚举控制器 → MI Admin Identify Controller 并逐字段比对设备侧数据
   → 两条错误路径（不支持的 MI 数据结构、不支持的 Admin 命令）。
② 上游官方测试套件（meson test，含 test/mi、test/mi-mctp）在 recipe 的 build()
   里跑 —— CI 的 host/build profile 同为 ohos-aarch64，是原生构建，真跑。

本测试的编译与链接**真依赖被测包**：CI 的 L1e(R34) 会把 lib/、include/ 移走后
重跑 conan test，届时本测试必须编译失败。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LibnvmemiTestConan(ConanFile):
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
            binary = os.path.join(self.cpp.build.bindirs[0], "test_libnvmemi")
            self.run(binary, env="conanrun")
        # ② 适配自检（M，非上游用例）：交付形态（库/头/pkg-config 契约/许可/纯净性）
        layout = os.path.join(self.source_folder, "test_layout.py")
        self.run("%s %s %s" % (sys.executable, layout,
                               self.dependencies["libnvmemi"].package_folder))
