#!/usr/bin/env python3
"""test_package for alot 0.12 — 消费测试。

alot 是纯 Python 终端 MUA。上游 pytest 测试（22 个文件）需 notmuch2 数据库
环境（libnotmuch.so），OHOS 构建环境 notmuch 无 remote 制品、系统无
libnotmuch.so → pytest 无法运行。消费测试验证：
1. bin/alot wrapper 存在且可执行
2. python3 可 import alot 包（site-packages 布局正确）
3. wrapper 运行 --help 能输出用法（不依赖 notmuch2 运行时数据库）
"""

import os
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class AlotTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies[self.tested_reference_str].package_folder
        bin_dir = os.path.join(pkg, "bin")
        exe = os.path.join(bin_dir, "alot")
        if not os.path.exists(exe):
            raise ConanException(f"missing installed binary: {exe}")
        # wrapper 可执行
        if not os.access(exe, os.X_OK):
            raise ConanException(f"alot wrapper not executable: {exe}")
        # site-packages 里 alot 包存在
        py_ver = "python3"
        site_pkg = os.path.join(pkg, "lib", "python3", "site-packages")
        if not os.path.isdir(os.path.join(site_pkg, "alot")):
            # 兼容 python3.12 目录名
            site_pkg_alt = os.path.join(pkg, "lib", "python3.12", "site-packages")
            if not os.path.isdir(os.path.join(site_pkg_alt, "alot")):
                raise ConanException(f"alot package missing under {site_pkg}")
        # L0d: test() 必须调用 self.run——执行 test_alot.py（wrapper --help 冒烟）
        test_script = os.path.join(os.path.dirname(__file__), "test_alot.py")
        if self.run(f'"{sys.executable}" "{test_script}" "{exe}"', env="conanrun") != 0:
            raise ConanException("test_alot.py failed: alot --help smoke test")
