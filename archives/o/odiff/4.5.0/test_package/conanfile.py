#!/usr/bin/env python3
"""Conan test_package for odiff 4.5.0 — 消费者冒烟测试（真实执行 bin/odiff）。

odiff 是 Zig 应用（application），test_package 不做 CMake 链接；build() 为空，
test() 通过 self.run 执行 test_odiff.py，真实生成 BMP 图像并用包内 bin/odiff
做对比，校验退出码与 diff 输出（R34 反空壳）。test_odiff.py 满足 L0c 门禁。
"""
import os
import sys

from conan import ConanFile


class OdiffTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        odiff = os.path.join(self.dependencies["odiff"].package_folder, "bin", "odiff")
        script = os.path.join(self.source_folder, "test_odiff.py")
        self.run(
            f'"{sys.executable}" "{script}" "{odiff}" "{self.build_folder}"',
            env="conanrun",
        )
        self.output.info("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"python test_odiff.py <odiff_bin> <workdir>\",\"discovered\":1,\"passedCount\":1}")
