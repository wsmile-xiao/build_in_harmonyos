#!/usr/bin/env python3
"""Conan test_package — clang18-ccache 18.1.8

L1 consumer test (R34): compiles a real C source through the installed
ccache compiler-wrapper CLI, verifies cache hit on the second identical
compile, links and runs the produced executable (L0c: real test source
files present in test_package/).
"""
import os

from conan import ConanFile


class CcacheTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # R34: actually execute the installed binary (version check)
        self.run(f'{bash} -c "ccache --version | head -1"', env="conanrun")
        # L0c/R34: 真实消费者用例——ccache 包装 OHOS clang 编译真实 C 源、
        # 验证缓存命中并运行产物（test_package 自带测试源文件）
        self.run(
            f'{bash} -c "cd / && TMPDIR=$(mktemp -d) bash '
            f'{os.path.join(os.path.dirname(__file__), "consumer_verify.sh")}"',
            env="conanrun",
        )
