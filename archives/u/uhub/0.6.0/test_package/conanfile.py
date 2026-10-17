#!/usr/bin/env python3
"""Conan test_package — uhub 0.6.0（application，显式命令消费者）。

在可运行目标二进制的机器（OHOS 真机）上真实执行包内可执行文件：
  uhub -V / uhub-passwd 用户库增删查（sqlite3 链接）/ uhub -C 配置解析（file_plugins 指向包内插件）。
交叉编译容器中无法执行目标二进制时（can_run=False）跳过。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy


class UhubTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "build"

    def generate(self):
        VirtualRunEnv(self).generate(scope="run")

    def build(self):
        copy(self, "test.sh", self.source_folder, self.build_folder)

    def test(self):
        if not can_run(self):
            self.output.info("Cannot run OHOS target binaries on this machine; skipping runtime test")
            return
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        # 该 worker 上 /system/bin/sh 无法直接 exec ELF，沿用本仓 afmize 配方的 CONFIG_SHELL 约定
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.exists(bash):
            bash = "bash"
        self.run(
            'UHUB_BIN="{}" UHUB_PASSWD_BIN="{}" UHUB_PLUGIN_DIR="{}" "{}" test.sh'.format(
                os.path.join(package_folder, "bin", "uhub"),
                os.path.join(package_folder, "bin", "uhub-passwd"),
                os.path.join(package_folder, "lib", "uhub"),
                bash,
            ),
            env="conanrun",
            cwd=self.build_folder,
        )
