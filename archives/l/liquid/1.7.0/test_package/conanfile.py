#!/usr/bin/env python3
"""Conan test_package — liquid 1.7.0 L1 link test.

验证消费者能正确 find_package(liquid) 并链接 libliquid.so。
上游头 `liquid/liquid.h` 公开 API 包含 resamp_crcf（分数速率重采样），
L1 链接测试以 AGC + NCO 对象创建/销毁验证 libliquid 可加载。

鸿蒙消费者用例 `liquid-ohos-test.c` 由 conanfile 单独编译运行，
验证重采样器在鸿蒙环境下的端到端可行性。
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import copy
from conan.tools.build import can_run


class LiquidTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # L1: 链接测试
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 鸿蒙消费者用例：独立编译（不依赖 CTest）
        consumer_src = os.path.join(self.source_folder, "consumer-case",
                                    "liquid-ohos-test.c")
        if os.path.isfile(consumer_src):
            self.build_consumer(consumer_src)

    def build_consumer(self, src):
        """编译 liquid_ohos_consumer，失败仅 warning（非阻塞，
        用例仅验证鸿蒙可行性，不替代 L1 测试）。"""
        try:
            # 获取头文件/库路径
            inc = self.dependencies["liquid"].cpp_info.includedirs[0]
            lib_dir = self.dependencies["liquid"].cpp_info.libdirs[0]
            lib = os.path.join(lib_dir, "libliquid.so")
            out = os.path.join(self.build_folder, "liquid_ohos_consumer")
            c = ("/data/service/hnp/bin/clang "
                 f"-I{inc} -o {out} {src} "
                 f"-L{lib_dir} -lliquid -lm")
            self.run(c)
        except Exception as e:
            self.output.warning(f"消费者用例编译跳过：{e}")

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # 运行消费者用例（如果编译成功）
        if can_run(self):
            consumer = os.path.join(self.cpp.build.bindirs[0], "liquid_ohos_consumer")
            if os.path.isfile(consumer):
                self.run(consumer, env="conanrun")
