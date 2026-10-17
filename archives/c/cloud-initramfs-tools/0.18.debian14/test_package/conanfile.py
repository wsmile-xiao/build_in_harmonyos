#!/usr/bin/env python3
"""Conan test_package for cloud-initramfs-tools 0.18.debian14.

L1 消费者测试：对已安装的包执行 test_cloud_initramfs_tools.sh。
套件 = 上游交付物真实执行（9 个上游入口的 prereqs 协议 + 打包 CLI 失败路径 +
CLI 工具解析两分支 + 配置默认值）+ 包布局契约 + 鸿蒙特有用例。
上游本身无自动化测试（清点证据见 MANIFEST.yml 与 reports/test-report.md §1）。
"""
import os
import shutil

from conan import ConanFile


class CloudInitramfsToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.recipe_folder, "test_cloud_initramfs_tools.sh")
        # OHOS 无 /bin/bash：优先 CONFIG_SHELL，其次 PATH 中的 bash，最后平台绝对路径
        bash = (os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" "{script}" "{package_folder}"', env="conanrun")
        self.output.info("cloud-initramfs-tools package verification suite passed")
