#!/usr/bin/env python3
"""Conan test_package — autotiling 1.9.3 消费者验证。

test() 内断言（R34 真实调用被测包 API）：
  1. python3 test_autotiling.py：import autotiling 校验 __version__ /
     get_parser() 参数解析 / save_string 文件写入 / temp_dir 非空
     （均不依赖 i3/sway 连接）
  2. bin/autotiling --version（argparse version 动作，不连 i3，退出码 0）
  3. bin/autotiling -h（help 动作，退出码 0）

PYTHONPATH 由 conanfile.py 的 package_info 注入；此处再显式 os.environ
注入保证脚本与 CLI 均可解析 autotiling 模块（i3ipc 随 pip 安装于同一
site-packages，airthings-ble 同模式）。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class AutotilingTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", ver, "site-packages")
        if not os.path.isdir(os.path.join(site, "autotiling")):
            raise ConanException(f"autotiling package missing under {site}")
        cli = os.path.join(pkg, "bin", "autotiling")
        test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "test_autotiling.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_autotiling.py missing: {test_script}")

        old_env = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = site + (os.pathsep + old_env if old_env else "")
        try:
            # 1) 消费者断言脚本（import / parser / file / tempdir + CLI 冒烟）
            ret = self.run(f"python3 '{test_script}' '{cli}' 2>&1")
            if ret != 0:
                raise ConanException(f"test_autotiling.py failed with exit code {ret}")
            # 2) CLI --version（argparse version 动作，不连 i3）
            ret = self.run(f"'{cli}' --version >/dev/null 2>&1")
            if ret != 0:
                raise ConanException(f"autotiling --version failed with exit code {ret}")
            # 3) CLI -h
            ret = self.run(f"'{cli}' -h >/dev/null 2>&1")
            if ret != 0:
                raise ConanException(f"autotiling -h failed with exit code {ret}")
        finally:
            if old_env is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old_env
