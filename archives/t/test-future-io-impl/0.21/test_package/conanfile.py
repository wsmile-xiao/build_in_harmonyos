#!/usr/bin/env python3
"""Conan test_package for test-future-io-impl 0.21 — consumer check (R34 真实 API).

通过 test_test_future_io_impl.py 驱动 perl 加载 <pkg> 中的
Test::Future::IO::Impl，并真实调用其唯一公开 API `run_tests`（配一份
Future::IO 桩实现，跑通 sleep 验收套件）。env="conanrun" 注入 is required
（裸 subprocess 会丢失 conanrun 环境注入，参见 perl-uri 先例教训）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class TestFutureIoImplTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["test-future-io-impl"].package_folder
        # 安装前缀随 perl 构建而异 → 遍历定位 Test/Future/IO/Impl.pm。
        # 模块相对路径三层，site 需上溯三级（不可返回末级目录）。
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "Impl.pm" in files and root.endswith(
                    os.path.join("Test", "Future", "IO")):
                site = os.path.dirname(os.path.dirname(os.path.dirname(root)))
                break
        if not site:
            raise ConanException("Test/Future/IO/Impl.pm not found in package")

        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_test_future_io_impl.py")
        if not os.path.isfile(test_script):
            raise ConanException(
                f"test_test_future_io_impl.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
