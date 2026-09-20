#!/usr/bin/env python3
"""Conan test_package for future-queue 0.52 — consumer check (R34 真实 API).

通过 test_future_queue.py 驱动 perl 消费者测试，载入**已打包**的 Future::Queue
并真实调用其全部公开 API（含 max_items 背压与 Future 异步语义）。

env="conanrun" 注入是必需的：本包 package_info() 与依赖 future 的 PERL5LIB 都由
runenv_info 声明，裸 subprocess 会丢失该注入。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class FutureQueueTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["future-queue"].package_folder
        # 安装前缀随 perl 构建而异 → 遍历定位 Future/Queue.pm，
        # 返回的 site 即包含该相对路径的 perl lib 根
        rel = os.path.join("Future", "Queue.pm")
        site = None
        for root, _dirs, _files in os.walk(pkg):
            if os.path.isfile(os.path.join(root, rel)):
                site = root
                break
        if not site:
            raise ConanException("Future/Queue.pm not found in package")

        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_future_queue.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_future_queue.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
