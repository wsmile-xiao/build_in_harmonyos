#!/usr/bin/env python3
"""Conan test_package for pdftoipe/7.2.29.2 — 安装产物消费者验证。

不使用 can_run() 门控：OHOS 侧 tools.build.cross_building:can_run=False 会让
can_run() 恒为 False，test() 被静默跳过而 conan create 仍 rc=0（假绿陷阱）。
本包的消费者测试必须在 OHOS aarch64 宿主上真实执行，失败即抛错。
"""
import os
import shutil

from conan import ConanFile


class PdftoipeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(self.dependencies["pdftoipe"].package_folder, "bin", "pdftoipe")
        script = os.path.join(self.source_folder, "test.sh")
        bash = shutil.which("bash") or "/data/service/hnp/bin/bash"
        # env="conanrun": libpoppler.so / libfreetype.so.6 由依赖包提供，需 LD_LIBRARY_PATH
        self.run('"{}" "{}" "{}"'.format(bash, script, bin_path), env="conanrun")
