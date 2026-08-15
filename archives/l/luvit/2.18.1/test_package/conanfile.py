#!/usr/bin/env python3
"""Conan test_package — luvit 2.18.1

L1 test: 运行 test_package/test.py（luvit --version + luvit -e 执行 Lua 代码）
验证 Lua 运行时可用。用 self.run() 真实执行（L0d 门禁要求）。
"""
import os

from conan import ConanFile


class LuvitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["luvit"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        luvit = os.path.join(bin_dir, "luvit")
        if not os.path.exists(luvit):
            self.output.error(f"luvit launcher not found: {luvit}")
            raise AssertionError("luvit launcher missing in package")
        # test.py 从包内执行（self.run 的 cwd 是 build 目录，测试脚本在 recipe 目录）
        test_py = os.path.join(self.recipe_folder, "test.py")
        if not os.path.exists(test_py):
            test_py = os.path.join(self.build_folder, "test.py")
        self.run(f"LUVIT_BIN={luvit} python3 {test_py}", env="conanrun")
