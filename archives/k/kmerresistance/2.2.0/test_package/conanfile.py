#!/usr/bin/env python3
"""Conan test_package - kmerresistance 2.2.0.

Runs the packaged kmerresistance binary through a functional smoke test
(test.sh): version banner, argument validation, and a full pipeline run
against a stub `kma` (KMA is an external runtime dependency, not shipped
in this package) with synthetic FASTQ + KMA result fixtures, verifying
the final .KmerRes/.res correlation output.
"""
import os
import shutil

from conan.tools.files import copy

from conan import ConanFile
from conan.tools.build import can_run


class KmerresistanceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def export(self):
        # 测试源文件（.sh）必须随 test_package 一起导出：CI L0c 门禁要求
        # test_package/ 下存在 .c/.cpp/.cc/.cxx/.sh/.py 测试源（E308/E255）。
        copy(self, "test_ohos.sh", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["kmerresistance"].package_folder
        bin_path = os.path.join(package_folder, "bin", "kmerresistance")

        assert os.path.isfile(bin_path), f"kmerresistance binary not found: {bin_path}"

        if can_run(self):
            shell = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash"
            )
            script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'"{shell}" "{script}" "{bin_path}"', env="conanrun")

            # rule12 鸿蒙特有测试：在 OpenHarmony 目标上追加平台断言
            # （平台三元组 / ELF64 指针宽度 / 动态依赖闭合），由 test_ohos.sh 执行。
            ohos_script = os.path.join(self.source_folder, "test_ohos.sh")
            if os.path.isfile(ohos_script):
                pkg_bin = os.path.dirname(bin_path)
                self.run(f'"{shell}" "{ohos_script}" "{pkg_bin}"', env="conanrun")
                self.output.info("HarmonyOS-specific test OK (rule12: triplet/pointer-width/dep-closure)")
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"kmerresistance is not an ELF binary: {magic!r}"
            self.output.info(f"kmerresistance binary exists and has ELF magic: {bin_path}")
