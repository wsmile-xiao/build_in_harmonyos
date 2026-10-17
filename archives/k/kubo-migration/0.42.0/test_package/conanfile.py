#!/usr/bin/env python3
"""Conan test_package for kubo-migration 0.42.0 — 真实执行 15→16 迁移。

kubo-migration 是纯 Go CLI（fs-repo-15-to-16）。本 test_package 不做只打印
"通过" 的空壳测试（R34/PF3），而是按上游 test-e2e/test.sh 的语义真实执行，
并含一项鸿蒙特有测试（OHOS 平台签名校验）：
0) 鸿蒙特有：用 OHOS 平台自带 binary-sign-tool display-sign 校验安装产物
   带合法 code signature（AppSpawn 拒绝未签名 ELF，签名是 OHOS 可运行前提）；
1) 运行 `fs-repo-15-to-16 -help` 冒烟；
2) 复制上游 repo-v15 fixture 为 repo-test，运行正向迁移，断言 version=16 且
   目录树与 repo-v16 fixture 完全一致（diff -r）；
3) 运行 -revert 回退，断言 version=15 且目录树与 repo-v15 fixture 完全一致。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class KuboMigrationTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["kubo-migration"].package_folder
        bin_path = os.path.join(package_folder, "bin", "fs-repo-15-to-16")

        if not os.path.isfile(bin_path):
            raise ConanException(f"fs-repo-15-to-16 binary not found: {bin_path}")

        if not can_run(self):
            # 交叉构建（不同 build/host profile）无法直接运行，至少验证 ELF 存在
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", (
                f"fs-repo-15-to-16 is not an ELF binary: {magic!r}"
            )
            self.output.info(
                f"kubo-migration cross-build: ELF present at {bin_path}"
            )
            return

        shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "/bin/sh"
        script = os.path.join(self.recipe_folder, "test_kubo_migration.sh")
        fixtures = self.recipe_folder  # 含 repo-v15/ 与 repo-v16/ 子目录
        work_dir = os.path.join(self.build_folder, "migrate-work")

        # R34 反空壳：此处通过 self.run 真实调用被测二进制执行迁移
        self.run(
            f'"{shell}" "{script}" "{bin_path}" "{fixtures}" "{work_dir}"',
        )
        self.output.info(
            "kubo-migration test PASSED (real 15->16 migration + revert)"
        )
