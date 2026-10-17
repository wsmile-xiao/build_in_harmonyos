#!/usr/bin/env python3
"""Conan test_package — qt5-qtsvgv 5.15.2.2 L1 test.

L1 test: 构建并运行 test.cpp——链接 Qt5Svg、解析最小合法 SVG 并断言
QSvgRenderer::isValid()==true，验证 libQt5Svg 库可用且解析核心正常。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Qt5QtSvgvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # qt5-qtsvg 包级目标不传递 qt5-qtbase 的 include 路径(test.cpp 需
        # QCoreApplication → QtCore 头) → 直接声明 qt5-qtbase 依赖,
        # CMakeDeps 生成其 config, 链接时带 QtCore/QtGui include
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_exe = os.path.join(self.cpp.build.bindir, "test_qt5svgv")
        self.run(test_exe, env="conanrun")
