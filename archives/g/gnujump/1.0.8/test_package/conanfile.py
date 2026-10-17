#!/usr/bin/env python3
"""Conan test recipe — gnujump headless startup + ELF structure checks.

无图形栈环境下的消费者验证（R34）：
  1. ELF 结构断言：AArch64 PIE、musl 解释器；
  2. DT_NEEDED 白名单：只允许 SDL 兼容链/GL 转译层/图像编解码依赖，
     拒绝 libX11/libasound 等桌面栈污染；
  3. 无头运行：SDL dummy 驱动 + timeout 保护，断言游戏完成 DSO 加载、
     SDL 初始化并推进到视频初始化/主循环（启动期行为断言）。
"""
import os
import struct
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class GnujumpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # runtime DSO chain：sdl12-compat 叠在 SDL2 上，gl4es 叠在系统 GLES 上
        self.requires("sdl12-compat/1.2.68", run=True)
        self.requires("sdl-image/1.2.12", run=True)
        self.requires("sdl-mixer/1.2.12", run=True)
        self.requires("gl4es/1.1.6", run=True)

    def test(self):
        if not can_run(self):
            self.output.info("交叉构建无法运行，消费者运行时断言按协议跳过")
            return
        dep = self.dependencies[self.tested_reference_str]
        script = os.path.join(self.recipe_folder, "test_gnujump.py")
        bindir = os.path.join(dep.package_folder, "usr", "bin")
        environment = Environment()
        # musl 忽略 DT_RUNPATH（§12.2）：传递依赖的 libdir 必须显式进
        # LD_LIBRARY_PATH，否则运行期加载 libjpeg/libtiff/libwebp 失败
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            for d in dep.cpp_info.aggregated_components().libdirs:
                environment.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, d))
        environment.define("SDL_VIDEODRIVER", "dummy")
        environment.define("SDL_AUDIODRIVER", "dummy")
        with environment.vars(self).apply():
            self.run(f'"{sys.executable}" "{script}" "{bindir}"')
