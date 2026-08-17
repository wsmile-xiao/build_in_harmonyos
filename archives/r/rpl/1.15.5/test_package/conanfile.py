#!/usr/bin/env python3
"""Conan test_package — rpl 1.15.5.

验证 rpl 可执行并完成实际文本替换（R34：实质调用被测包）。
调用 test_rpl.sh 测试脚本（L0c 门禁要求 test_package/ 有测试源文件）。
"""
import os
import shutil
import sys
import tempfile

from conan import ConanFile


class RplTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["rpl"].package_folder, "bin")
        site = os.path.join(
            self.dependencies["rpl"].package_folder,
            "lib", "python3.12", "site-packages",
        )
        script = os.path.join(self.source_folder, "test_rpl.sh")
        # sample.txt 写入 TMPDIR（非 HMDFS）：CI 的 test_package 目录
        # （buildbot-worker/HMDFS）中 rpl 的临时文件+rename 替换失败
        # （本地普通文件系统成功）→ 用 tempfile.mkdtemp（TMPDIR）
        tmp = tempfile.mkdtemp(prefix="rpl-test-")
        os.chmod(tmp, 0o755)
        # 显式注入 PYTHONPATH（conanrun 聚合可能不含 rpl 的 site-packages，
        # rpl 启动需 chardet/regex/chainstream → import 失败即退出）
        # $3=sys.executable：CI 的 conanrun 不含 buildenv 的 python PATH
        self.run(
            f'PYTHONPATH="{site}" sh "{script}" "{bin_dir}" '
            f'"{tmp}" "{sys.executable}"',
            env="conanrun",
        )
        shutil.rmtree(tmp, ignore_errors=True)
