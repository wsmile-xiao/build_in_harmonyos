#!/usr/bin/env python3
"""Conan test_package for packmol 21.2.3 (Conan L1 official test).

实质验证（非空壳），覆盖两条消费路径：
  1) 绝对路径调用 run_smoke.sh：固定 seed 的 PDB 水盒打包，断言输出 PDB 含
     TITLE/HETATM/Success（packmol 无 --version，未知参数码 174 退出）。
  2) 消费端 PATH 调用：conanrun 环境把包 bin/ 注入 PATH，以命令名 `packmol`
     直接调用（等价上游 python/tests/test_packmol.py 的
     subprocess.run(["packmol"], ...) 用例），断言 output.xyz 生成。
注：packmol 将输出写到当前工作目录，测试在独立子目录运行。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import copy


class PackmolTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["packmol"].package_folder
        packmol = os.path.join(pkg, "bin", "packmol")
        if not os.path.isfile(packmol):
            raise Exception("packmol binary not found in package: {}".format(packmol))

        # packmol 把输出写到当前工作目录；在独立子目录运行，避免在
        # test_package 源码树中留下 PDB/日志产物。
        run_dir = os.path.join(self.build_folder, "smoke_run")
        shutil.rmtree(run_dir, ignore_errors=True)
        os.makedirs(run_dir, exist_ok=True)
        for name in (
            "run_smoke.sh",
            "smoke.inp",
            "structure.pdb",
            "packmol_xyz.inp",
            "water.xyz",
        ):
            copy(self, name, src=self.source_folder, dst=run_dir)

        # 1) 绝对路径调用：固定 seed 真实打包（PDB 输入 -> PDB 输出，断言
        #    TITLE/HETATM/Success）。packmol 不提供 --version（未知参数码 174）。
        self.run(
            'sh run_smoke.sh "{pm}"'.format(pm=packmol),
            cwd=run_dir,
            env="conanrun",
        )

        # 2) 消费端 PATH 调用：conanrun 把 packmol/bin 注入 PATH，以命令名
        #    `packmol` 直接调用——等价复现上游 python/tests/test_packmol.py
        #    （subprocess.run(["packmol"], ...) + 断言输出文件存在）。
        self.run(
            "packmol < packmol_xyz.inp > xyz_run.log 2>&1",
            cwd=run_dir,
            env="conanrun",
        )
        if not os.path.isfile(os.path.join(run_dir, "output.xyz")):
            raise Exception(
                "packmol PATH consumer run failed: output.xyz was not generated"
            )