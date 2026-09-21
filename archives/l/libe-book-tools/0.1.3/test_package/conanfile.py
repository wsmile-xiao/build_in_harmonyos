#!/usr/bin/env python3
"""test_package —— libe-book-tools 0.1.3 消费者测试。

从消费者视角驱动交付的三个命令行转换器（不链任何库：本包只交付 bin/）。
断言与条数全部由 test_libe_book_tools.sh 自己打印，这里只负责把包路径交给它、
并把它声明的失败如实变成 conan test 的失败（CI L1e 破坏性反向验证要求移走
bin/ 之后本测试必须失败）。
"""

import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class LibebookToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        # basic_layout 而非 cmake_layout：本测试不编译 C++ 消费者，用 cmake 会
        # 在 test_package/ 里落下 CMakeUserPresets.json 与 build/ 生成物
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        tested = self.dependencies["libe-book-tools"]
        package_folder = tested.package_folder
        bindir = os.path.join(package_folder, "bin")
        script = os.path.join(self.source_folder, "test_libe_book_tools.sh")
        workdir = os.path.join(self.build_folder, "consumer-run")
        os.makedirs(workdir, exist_ok=True)
        if not os.path.isfile(script):
            raise RuntimeError(f"consumer test script missing: {script}")
        # env="conanrun" 提供依赖包（libxml2 等共享库）的运行期库路径
        self.run(f'sh "{script}" "{bindir}" "{workdir}" "{package_folder}"',
                 env="conanrun")
