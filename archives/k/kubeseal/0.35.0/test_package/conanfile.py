#!/usr/bin/env python3
"""Conan test_package for kubeseal 0.35.0 — 消费者用例真跑交付出来的二进制。

上游测试（`go test -count=1 -json -timeout 300s ./...`）已在 conanfile.py 的
build() 阶段真跑，按包统计并在日志中逐条打印失败/跳过（9 个上游测试包、68 条
离线确定性用例为硬门禁：不得有失败、不得少跑；唯一环境依赖用例
pkg/controller/TestHttpCert 固定占用 TCP :8080，已单独分类打印）。

本 test_package 负责消费者视角：把 bin/kubeseal 与 bin/controller 当黑盒真跑
11 个用例（版本串、--help、**离线 SealedSecret 加解密往返**（json 与 yaml 两条
路径）、用错私钥必须解不开、缺证书文件、非法输入，以及控制器的版本/帮助），
并附带 14 项交付形态自检（M1–M14）。
R34 反空壳：把 package 的 bin/ 挪走后本测试必然失败。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class KubesealTestConan(ConanFile):
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
        dependency = self.dependencies["kubeseal"]
        package_folder = dependency.package_folder
        script = os.path.join(self.recipe_folder, "consumer_check.py")
        argv = [sys.executable, script, package_folder,
                "--expect-machine", self._expected_machine(),
                "--expect-version", "v%s" % dependency.ref.version]
        if str(self.settings.os) == "OHOS":
            argv.append("--require-signature")
        command = " ".join('"%s"' % item for item in argv)
        self.output.info("consumer check: %s" % command)
        self.run(command, env="conanrun")
