#!/usr/bin/env python3
"""Consumer test_package for sprng 2.0a.

从**已安装包**的角度验证：头文件可 include、静态库可链接（含 pmlcg→gmp 的
传递依赖）、生成器数值性质与确定性、以及 pack/unpack 往返。
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class SprngTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cannot run target binaries here; consumer build only")
            return
        # cmake_layout 下 test() 的 cwd 是 build 目录 ⇒ 一律绝对路径（先例 #5）
        exe = os.path.join(self.build_folder, "test_sprng")
        self.run(exe, env="conanrun")
