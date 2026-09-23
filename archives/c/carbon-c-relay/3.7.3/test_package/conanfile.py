#!/usr/bin/env python3
"""Conan test_package — carbon-c-relay 3.7.3 消费者测试。

test.sh 驱动打包出的 relay 二进制做真实行为断言：
1. -v 版本横幅包含 v3.7.3；
2. configtest 模式（-t -f）真实解析一份集群转发配置，
   断言退出码 0 且输出 "parsed configuration follows"。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CarbonCRelayTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["carbon-c-relay"].package_folder
        bin_path = os.path.join(package_folder, "bin", "relay")
        assert os.path.isfile(bin_path), "relay binary not found: %s" % bin_path

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            self.run('"%s" "%s" "%s" "%s"' % (
                shell, test_script, bin_path, package_folder), cwd=cwd)
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", "relay is not an ELF binary"
            self.output.info("relay binary exists and has ELF magic: %s" % bin_path)
