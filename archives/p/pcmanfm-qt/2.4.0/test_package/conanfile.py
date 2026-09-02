#!/usr/bin/env python3
"""Conan test_package — pcmanfm-qt.

pcmanfm-qt is a Qt6 GUI file manager. The test compiles a small C smoke-test
binary (CI L0c no_test_sources gate requires a compilable test source), then
verifies the packaged executable with the offscreen Qt platform (no display
server needed):
  1. bin/pcmanfm-qt exists in the package (checked before running)
  2. smoke-test binary runs `pcmanfm-qt --version` and `--help`, both exit 0
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class PcmanfmqtTestConan(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        bindir = self.dependencies["pcmanfm-qt"].cpp_info.bindirs[0]
        exe = os.path.join(
            self.dependencies["pcmanfm-qt"].package_folder, bindir, "pcmanfm-qt")
        # 1) 可执行文件必须存在于包内
        if not os.path.exists(exe):
            raise Exception(f"pcmanfm-qt executable not found: {exe}")
        if cross_building(self):
            self.output.info("cross-building: 编译验证通过，跳过运行时测试")
            return
        # 2) 运行 smoke-test 二进制（--version / --help 均要求退出码 0）
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_pcmanfm_qt")
        self.run(f'QT_QPA_PLATFORM=offscreen "{test_bin}"', env="conanrun")