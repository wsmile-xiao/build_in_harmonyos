#!/usr/bin/env python3
"""test_package — planarity 的消费者（下游）验证。

两条独立路径：
  1) 库消费者：test_planarity.c 通过 CMakeDeps 找到 planarity::planarity，
     链接 libplanarity 并真实调用公共图算法 API（42 条断言，见该文件头部）。
  2) CLI 消费者：test_cli.sh 调用安装树 bin/planarity，跑帮助/版本、安装树自带
     samples 上的完整上游 -test 套件、以及平面/非平面功能性出口码（7 条断言）。

关于 `run=True`：本包默认 shared=False → package_type 解析为 static-library，
Conan 对 `require.run=False` 的依赖既不在 CMakeDeps 里保留 bin 路径，也不在
VirtualRunEnv 里注入 PATH（conan/tools/env/virtualrunenv.py:
`if require.run: _prepend_path("PATH", ...)`）。而本包**确实交付可执行文件**
（bin/planarity），消费者需要能运行它，因此这里显式声明 run=True；
同时仍把二进制绝对路径作为参数传给脚本，避免依赖生成器的隐式行为。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PlanarityTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True：本包含可执行文件，消费者要运行 bin/planarity
        self.requires(self.tested_reference_str, run=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return

        # 1) 库消费者：CTest 驱动 test_planarity（真实链接被测库）
        cmake = CMake(self)
        cmake.test()

        # 2) CLI 消费者：必须用 bash 包一层——OHOS 的 /system/bin/sh 不能直接
        #    执行 ELF（templates/test_package-executable 同口径）。
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_cli.sh")
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "/data/service/hnp/bin/bash"
        dep = self.dependencies[self.tested_reference_str]
        planarity_bin = os.path.join(dep.package_folder, "bin", "planarity")
        self.run(f'"{bash}" "{script}" "{planarity_bin}"', env="conanrun")
