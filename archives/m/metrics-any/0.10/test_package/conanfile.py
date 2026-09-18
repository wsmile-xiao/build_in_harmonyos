#!/usr/bin/env python3
"""Conan test_package for metrics-any 0.10 — consumer check (R34 真实 API).

通过 test_metrics_any.py 驱动 perl 加载 <pkg> 中的 Metrics::Any 与各适配器并
真实调用其 API。env="conanrun" 注入 is required（裸 subprocess 会丢失
conanrun 环境注入，参见 perl-uri 先例的 FileNotFoundError 教训）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class MetricsAnyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["metrics-any"].package_folder
        # 安装前缀随 perl 构建而异 → 遍历定位 Metrics/Any.pm。
        # 模块在 <site>/Metrics/Any.pm，故 site = "Metrics" 目录的父级
        # （不可返回 Metrics/ 本身，否则 -I 指向错误层级）。
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "Any.pm" in files and os.path.basename(root) == "Metrics":
                site = os.path.dirname(root)
                break
        if not site:
            raise ConanException("Metrics/Any.pm not found in package")

        test_script = os.path.join(os.path.dirname(__file__), "test_metrics_any.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_metrics_any.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
