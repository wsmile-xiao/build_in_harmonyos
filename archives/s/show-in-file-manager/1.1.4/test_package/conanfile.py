#!/usr/bin/env python3
"""Conan test_package — show-in-file-manager 1.1.4 消费者验证。

test() 内断言（L0d 要求 test() 必须调用 self.run）：
  1. python3 smoke.py：导入 showinfm 并验证 API、URI 工具函数与 CLI 入口
  2. bin/showinfilemanager --version（真实 CLI，退出码 0）
  3. bin/showinfilemanager -h（真实 CLI，退出码 0）

PYTHONPATH 由 conanfile.py 的 package_info 注入；此处再显式 os.environ 注入
保证 smoke.py 与 CLI 均可解析 showinfm 模块（conan 2.29 self.run 的 env
参数仅接受 list，故改用 os.environ 临时注入）。
"""
import os
import sys

from conan import ConanFile


class ShowInFileManagerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # OHOS profile 的 os.version 不是本配方消费的 settings 项
        self.settings.rm_safe("os.version")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        site_packages = os.path.join(
            pkg, "lib",
            "python{}.{}".format(sys.version_info.major, sys.version_info.minor),
            "site-packages")
        cli = os.path.join(pkg, "bin", "showinfilemanager")
        smoke = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke.py")

        old_env = os.environ.get("PYTHONPATH")
        old_cli = os.environ.get("CLI_PATH")
        os.environ["PYTHONPATH"] = site_packages + (os.pathsep + old_env if old_env else "")
        os.environ["CLI_PATH"] = cli
        try:
            # 1) 断言脚本（import / API / URI 工具 / 平台识别）
            ret = self.run("python3 {} 2>&1".format(smoke))
            if ret != 0:
                raise Exception(f"test_package smoke.py failed with exit code {ret}")
            # 2) CLI smoke（--version 与 -h 退出码 0）
            ret = self.run("{} --version >/dev/null 2>&1".format(cli))
            if ret != 0:
                raise Exception(f"showinfilemanager --version failed with exit code {ret}")
            ret = self.run("{} -h >/dev/null 2>&1".format(cli))
            if ret != 0:
                raise Exception(f"showinfilemanager -h failed with exit code {ret}")
        finally:
            if old_env is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old_env
