#!/usr/bin/env python3
"""Conan test_package for future 0.52 — consumer check (R34 真实 API).

通过 test_future.py 驱动 perl 加载 <pkg> 中的 Future 模块并真实调用其 API。
env="conanrun" 注入 is required（裸 subprocess 会丢失 conanrun 环境注入，
参见 perl-uri 先例的 FileNotFoundError 教训）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class FutureTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["future"].package_folder
        # 安装前缀随 perl 构建而异（site_perl/5.42.2 等）→ 遍历定位 Future.pm
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "Future.pm" in files:
                site = root
                break
        if not site:
            raise ConanException("Future.pm not found in package")

        test_script = os.path.join(os.path.dirname(__file__), "test_future.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_future.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
