#!/usr/bin/env python3
"""Conan test_package for kubergrunt 0.19.0 — 消费者用例真跑交付出来的二进制。

上游测试（`go test -count=1 -json -timeout 300s ./...`）已在 conanfile.py 的
build() 阶段真跑，并逐条打印统计（离线确定性用例是硬门禁）。

本 test_package 负责消费者视角：把 bin/kubergrunt 当黑盒真跑
（--version / --help / 各子命令 --help / 缺失必填参数与非法参数三条失败路径），
断言真实 stdout、stderr 与退出码，并附带 13 项交付形态自检（M1–M13）。
R34 反空壳：把 package 的 bin/ 挪走后本测试必然失败。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class KubergruntTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def _expected_machine(self):
        arch = str(self.settings.arch)
        if arch in ("armv8", "arm64", "aarch64"):
            return "aarch64"
        if arch in ("x86_64", "amd64"):
            return "x86_64"
        raise ConanException("unsupported arch for consumer check: %s" % arch)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: runtime consumer check skipped")
            return
        dependency = self.dependencies["kubergrunt"]
        package_folder = dependency.package_folder
        script = os.path.join(self.recipe_folder, "consumer_check.py")
        argv = [sys.executable, script, package_folder,
                "--expect-machine", self._expected_machine(),
                "--expect-version", str(dependency.ref.version)]
        if str(self.settings.os) == "OHOS":
            argv.append("--require-signature")
        command = " ".join('"%s"' % item for item in argv)
        self.output.info("consumer check: %s" % command)
        self.run(command, env="conanrun")
