#!/usr/bin/env python3
"""test_package for aspell-compat 0.60.8.2.

aspell-compat 是纯脚本子包（ispell/spell 兼容脚本）。R34：测试必须实质依赖被测包。
由于 OHOS 安全模型下未签名二进制不可执行（与 aspell 主包 test_package 一致），
本测试调用 test_compat.sh（CI L0c 要求的测试源文件）实质验证被测包：
  1. 校验 bin/ispell、bin/spell 存在且可执行；
  2. 对两个脚本执行 `sh -n` 语法校验（即实际调用 shell 解析器）；
  3. 校验脚本内容确实包装/调用 aspell CLI（grep aspell）。
"""
import os

from conan import ConanFile


class AspellCompatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["aspell-compat"]
        bin_dir = os.path.join(str(dep.package_folder), "bin")

        # 实质校验委托给 test_compat.sh（CI L0c 要求的测试源文件）；
        # self.run 走 conanrun 环境（与 aspell 主包 test_package 同策略）。
        test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_compat.sh")
        self.run(f"sh {test_script} '{bin_dir}'", env="conanrun")
        self.output.info("✅ ispell/spell: exists, executable, valid sh, wraps aspell")
