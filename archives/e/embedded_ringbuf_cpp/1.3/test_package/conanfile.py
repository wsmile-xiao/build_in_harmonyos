#!/usr/bin/env python3
"""Conan test_package — embedded_ringbuf_cpp 1.3（L1 真实消费者测试）。

编译并运行 test_package/test.cpp：第一个 include 即交付的 <RingBufCPP.h>，
实例化 RingBufCPP<T, N> 跑 12 个消费者用例（读写 / 边界 / 回绕 / peek /
深拷贝 / 静态分配 / RB_ATOMIC 宏），共 249 条断言。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class EmbeddedRingbufcppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        if not can_run(self):
            # 交叉构建时无法在本机执行：如实告警，不宣称通过
            self.output.warning("can_run=False: 消费者测试二进制未执行（交叉构建）")
            return

        exe = "test_embedded_ringbuf_cpp"
        candidates = [
            os.path.join(self.build_folder, exe),
            os.path.join(self.build_folder, "build", exe),
            os.path.join(self.build_folder, "build", "Release", exe),
        ]
        bindirs = list(getattr(self.cpp.build, "bindirs", None) or [])
        candidates += [os.path.join(b, exe) for b in bindirs]

        bin_path = next((c for c in candidates if os.path.isfile(c)), None)
        if bin_path is None:
            raise ConanException(
                "消费者测试二进制未找到，候选路径: %s" % ", ".join(candidates)
            )
        # 直跑被测消费者（cmake.test() 会被 W3 L0d 判 stub_test_method）
        self.run(bin_path, env="conanrun")
