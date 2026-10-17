#!/usr/bin/env python3
"""Conan test_package for test-metrics-any 0.01 — consumer check (R34 真实 API).

通过 test_test_metrics_any.py 驱动 perl 消费者测试，载入**已打包**的
Test::Metrics::Any 并真实调用其导出 API。

env="conanrun" 注入是必需的：本包 package_info() 与依赖 metrics-any 的
PERL5LIB 都由 runenv_info 声明，裸 subprocess 会丢失该注入
（参见 perl-uri 先例的 FileNotFoundError 教训）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class TestMetricsAnyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["test-metrics-any"].package_folder
        # 安装前缀随 perl 构建而异 → 遍历定位 Test/Metrics/Any.pm，
        # 返回的 site 即包含该相对路径的 perl lib 根
        rel = os.path.join("Test", "Metrics", "Any.pm")
        site = None
        for root, _dirs, _files in os.walk(pkg):
            if os.path.isfile(os.path.join(root, rel)):
                site = root
                break
        if not site:
            raise ConanException("Test/Metrics/Any.pm not found in package")

        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_test_metrics_any.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_test_metrics_any.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
