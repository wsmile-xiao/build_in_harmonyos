#!/usr/bin/env python3
"""test_package/conanfile.py — libetonyek-tools 消费者测试驱动。

消费者视角：装完包只用 `bin/` 里的命令行工具（不链库、不带头文件），所以这里
不调 CMake，直接跑 test_tools.sh 断言工具的存在性、ELF 架构、版本自述、用法路径
与错误路径。TMPDIR 显式指向本次 test 的构建目录——真机 /tmp 只读。
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class LibetonyekToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["libetonyek-tools"].package_folder
        bindir = os.path.join(package, "bin")
        workdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(workdir, exist_ok=True)
        # 脚本复制到可写目录再执行；真机 /tmp 只读，TMPDIR 也指向这里。
        copy(self, "test_tools.sh", src=self.recipe_folder, dst=workdir)
        command = (f'TMPDIR="{workdir}" bash "{workdir}/test_tools.sh" '
                   f'"{bindir}"')
        self.output.info(f"运行消费者测试: {command}")
        self.run(command, env="conanrun", cwd=workdir)
