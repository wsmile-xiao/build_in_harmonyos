#!/usr/bin/env python3
"""Conan test_package — clang-build-analyzer 1.6.0.

ClangBuildAnalyzer 是命令行工具(TOOL 类型),测试方式:
1. 验证可执行文件存在于 package 的 bin/ 目录
2. 若可执行(can_run,非交叉编译):运行 ClangBuildAnalyzer 无参数,
   应输出 usage 信息并返回非零退出码
3. 交叉编译时(OHOS aarch64 on x86_64 CI worker):仅验证二进制存在,
   通过 cross_building 检查跳过执行(R34 实质依赖被测包的二进制)
"""
import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class ClangBuildAnalyzerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 1. 验证二进制存在于 package 中
        dep = self.dependencies["clang-build-analyzer"]
        binary = os.path.join(dep.package_folder, "bin", "ClangBuildAnalyzer")
        if not os.path.isfile(binary):
            raise Exception(f"ClangBuildAnalyzer binary not found at {binary}")

        # 2. 交叉编译时跳过执行(CI worker 是 x86_64,无法运行 aarch64 二进制)
        if cross_building(self):
            self.output.info("Cross-building detected, skipping binary execution test.")
            return

        if not can_run(self):
            self.output.info("can_run returned False, skipping binary execution test.")
            return

        # 3. 运行二进制:无参数时应输出 usage 并返回非零
        # R34: test 实质依赖被测包的二进制
        script = os.path.join(self.source_folder, "test.sh")
        ret = self.run(f'bash "{script}" "{binary}"', env="conanrun")
        # self.run 在 Conan 2.x 中,非零退出码会抛 ConanException,
        # 所以如果到这里说明测试通过
        self.output.info("ClangBuildAnalyzer test passed.")
