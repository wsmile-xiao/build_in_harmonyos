#!/usr/bin/env python3
"""Conan test_package — irrtoolset 5.1.3 实质功能测试.

通过调用安装后的真实 CLI 工具 (rpslcheck/peval/rtconfig) 验证
公开功能: 合法/非法 RPSL 对象校验、路由策略过滤器求值、配置生成.
"""
import os

from conan import ConanFile


class IrrtoolsetTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")