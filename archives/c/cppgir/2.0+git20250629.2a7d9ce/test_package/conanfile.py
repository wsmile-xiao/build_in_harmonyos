#!/usr/bin/env python3
"""Test package for cppgir 2.0+git20250629.2a7d9ce.

验证安装的 cppgir 生成器可用：用最小 Test-1.0.gir（一个 gint test_add(gint,gint)
函数）跑生成，断言输出文件树完整且 _functions.hpp 含 add 绑定声明。
工具运行需要 fmt 运行库（LD_LIBRARY_PATH 由 conanrun 提供）。
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class CppgirTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        if cross_building(self) and not can_run(self):
            self.output.info("cross-building: skip runtime test")
            return
        dep = self.dependencies["cppgir"]
        cppgir_bin = os.path.join(dep.package_folder, "bin", "cppgir")
        test_dir = os.path.dirname(__file__)
        gir_dir = test_dir
        out_dir = os.path.join(self.build_folder, "gen")
        script = os.path.join(test_dir, "test_cppgir_generation.sh")
        # 运行驱动脚本：用最小 GIR 驱动 cppgir 生成并断言绑定内容
        # （conanrun 提供 libc++_shared.so/fmt 的 LD_LIBRARY_PATH）
        self.run('{} "{}" "{}" "{}"'.format(script, cppgir_bin, gir_dir, out_dir),
                 env="conanrun")
