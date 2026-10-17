#!/usr/bin/env python3
"""Conan test_package — clang22-ccache 22.1.8

L1 smoke test: verifies the installed ccache binary reports its version
and can be invoked as a compiler wrapper (consumer perspective, R34).
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
        # R34: actually execute the installed binary
        self.run(f'{bash} -c "ccache --version | head -1"', env="conanrun")
        # 验证可作为编译器包装器运行（调用 --zero-stats 即触发）
        self.run(f'{bash} -c "ccache --zero-stats && ccache --show-stats | head -5"', env="conanrun")
        # 消费者用例：ccache 包装 OHOS clang 编译 + 缓存命中 + 产物运行
        self.run(
            f'{bash} -c "cd / && TMPDIR=$(mktemp -d) bash '
            f'{os.path.join(os.path.dirname(__file__), "consumer_verify.sh")}"',
            env="conanrun",
        )