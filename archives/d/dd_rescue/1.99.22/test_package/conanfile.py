#!/usr/bin/env python3
"""test_package for dd_rescue — 真实执行验证（R34）。

不满足于"文件存在"，而是：
  ① 真实执行 dd_rescue -V 断言版本号；
  ② **真实做一次数据复制**并逐字节比对（核心功能，非空壳）；
  ③ 真实加载插件完成哈希计算（验证 libddr_* 可被 dlopen）；
  ④ 负向用例：不存在的输入文件必须失败（证明断言非恒真）。
产出全部落在 build 目录的子目录，避免污染源码目录被误提交（R19 教训）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import chmod
from conan.tools.layout import basic_layout


class DdRescueTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("dd_rescue: 交叉编译场景，跳过运行期测试")
            return

        # ⚠️ 注意：test_package 中的 `self.package_folder` 指向 **test_package 自己**，
        # 不是被测包。取被测包目录必须走 self.dependencies。
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        if not pkg_folder:
            raise ConanException(
                f"无法解析被测包 {self.tested_reference_str} 的 package_folder")

        script = "run_dd_rescue_tests.sh"
        chmod(self, os.path.join(self.source_folder, script), execute=True)
        # 产物输出到 build_folder 子目录，避免污染源码目录
        outdir = os.path.join(self.build_folder, "_ddrescue_test")
        os.makedirs(outdir, exist_ok=True)
        self.run(f'sh "{os.path.join(self.source_folder, script)}" '
                 f'"{pkg_folder}" "{outdir}"')
