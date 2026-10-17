#!/usr/bin/env python3
"""Conan test_package — libformw 6.6_p20260516.

Compiles a form-based program against the packaged headers and statically
links libformw.a; at runtime it exercises the field/form lifecycle. The
curses.h transitively included by form.h comes from the visible ncurses/6.6
dependency, and libncursesw.a from the same package resolves at link time —
proving the same-source ABI pairing end to end.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibformwTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # form.h 公开头展开需要 curses.h：显式直接依赖，保证 CMakeDeps
        # 为 ncurses 生成完整 include 数据（传递依赖会被 Conan 2 置空，
        # libgmpxx 同款处理）
        self.requires("ncurses/6.6")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 实跑 form API 全链路（无终端依赖的内存操作路径）
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_form_api")
        self.run(f"{bin_path}", env="conanrun")
