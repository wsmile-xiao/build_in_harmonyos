#!/usr/bin/env python3
"""Conan recipe — gamelib 1.9.9 (header-only C++11 game library).

gamelib 是 skywind3000 的单头文件 2D 游戏开发库：
  - GameLib.h       — Win32 GDI 后端（Windows 专用，零外部依赖）
  - GameLib.SDL.h   — SDL2 后端（跨平台：Windows/Linux/macOS/Web/OHOS）

OHOS 适配使用 GameLib.SDL.h：SDL2 已发布到 ohpcd 制品仓（sdl2/2.30.10），
作为本包运行时/编译期依赖；SDL2_image/ttf/mixer 为可选扩展，头文件按
__has_include 自动探测，未提供时自动降级为纯 SDL2 核心能力。

上游无库级构建系统（仅 examples/Makefile 编译示例），本配方按 header-only
打包两个头文件；test_package 以消费者视角包含 GameLib.SDL.h 并实际调用
公开 API 验证编译、链接与运行（R34）。
"""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class GamelibConan(ConanFile):
    name = "gamelib"
    version = "1.9.9"
    description = "Single-header C++11 2D game library for beginners (Win32 GDI + SDL2 backends)"
    license = "MIT"
    homepage = "https://github.com/skywind3000/GameLib"
    url = ""  # CI fills this
    topics = ("game", "2d", "header-only", "sdl2", "c++11")

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # GameLib.SDL.h 需要 SDL2 头文件与库（transitive 使下游直接可见）
        self.requires("sdl2/2.30.10", transitive_headers=True, transitive_libs=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：无编译步骤；应用 conandata 声明的补丁（当前 patches 为空）
        apply_conandata_patches(self)

    def package(self):
        # 两个公开头文件（GameLib.h 为 Win32 专用，GameLib.SDL.h 为跨平台）
        copy(self, "GameLib.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "GameLib.SDL.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
