#!/usr/bin/env python3
"""Conan test_package — mypaint-brushes 2.0.2.1 消费者测试.

两个层次（R34 实质校验）:
  1. mypaint_brush_probe（C++ 消费者探针，CMake 构建）: 通过
     dep.cpp_info.resdirs 定位包内笔刷目录，实质解析 order.conf、
     校验 7 组笔刷目录与全部 .myb 纯 JSON 文件真实可读——与已合入
     kicad-demos 10.0.4 的 kicad_demo_probe 同款范式。
  2. test_mypaint_brushes.sh（数据完整性）: 打包布局 / order<->disk
     互证 / pc 文件声明 / 数据包纯度（无 lib/ bin/）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MypaintbrushesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dep = self.dependencies["mypaint-brushes"]
        brushes = os.path.join(dep.package_folder, dep.cpp_info.resdirs[0])
        if not os.path.isdir(brushes):
            raise Exception(f"mypaint-brushes resource dir not found: {brushes}")

        # 1) 数据完整性脚本（真机 CONFIG_SHELL 提供 bash）
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_mypaint_brushes.sh")
        self.run(f'"{bash}" "{script}" "{dep.package_folder}"', env="conanrun")

        # 2) C++ 消费者探针（交叉编译 OHOS 目标时推迟到目标端运行）
        if not can_run(self):
            self.output.info("Cross-built mypaint_brush_probe; runtime "
                             "verification deferred to the OHOS target")
            return
        probe = os.path.join(self.cpp.build.bindir, "mypaint_brush_probe")
        self.run(f'"{probe}" "{brushes}"', env="conanrun")
