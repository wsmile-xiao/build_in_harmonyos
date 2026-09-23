#!/usr/bin/env python3
"""Conan test_package — 消费者视角验证 libopenrazer 0.4.0。

libopenrazer 是 Qt wrapper（无 D-Bus daemon 环境下仍可验证：
构造 Manager 仅注册元类型；isDaemonRunning() 在无 daemon 时返回 false 不抛异常）。

说明：qtbase 采用 cmake_find_mode=none（自带 Qt6Config.cmake），CMakeDeps 不为
其生成配置文件；若经由 CMakeDeps 的 libopenrazer-config.cmake 触发
find_dependency(qtbase) 会失败。因此本 test_package 参照 qca/adwaita-qt 先例，
不依赖 CMakeDeps 解析 libopenrazer，而是显式注入 include/lib 路径 + Qt6_DIR。
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class LibopenrazerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Qt6 头文件/库（libopenrazer 公共头文件包含 QDBus* 等 Qt 头文件）
        self.requires("qtbase/6.11.1.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()
        tc = CMakeToolchain(self)
        pkg = self.dependencies["libopenrazer"]
        qtbase = self.dependencies["qtbase"]
        tc.variables["LIBOPENRAZER_INCLUDE_DIR"] = os.path.join(
            pkg.package_folder, "include"
        )
        tc.variables["LIBOPENRAZER_LIBRARY_DIR"] = os.path.join(
            pkg.package_folder, "lib"
        )
        # qtbase 采用 cmake_find_mode=none，自带 Qt6Config.cmake，
        # 显式指向其 cmake 目录供 find_package(Qt6) 解析
        tc.cache_variables["Qt6_DIR"] = os.path.join(
            qtbase.package_folder, "lib", "cmake", "Qt6"
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                self.output.error("test_package has no build bindir")
                raise SystemExit(1)
            executable = os.path.join(bindirs[0], "test_libopenrazer")
            # 测试二进制运行需要各依赖动态库（libopenrazer/Qt6 等）与
            # 系统 libc++_shared.so（/system/lib64）；显式注入 LD_LIBRARY_PATH。
            env = Environment()
            for p in self.dependencies.values():
                if p.package_folder:
                    libdir = os.path.join(p.package_folder, "lib")
                    if os.path.isdir(libdir):
                        env.prepend_path("LD_LIBRARY_PATH", libdir)
            env.prepend_path("LD_LIBRARY_PATH", [
                "/system/lib64/platformsdk",
                "/system/lib64/chipset-pub-sdk",
                "/system/lib64",
                "/system/lib64/ndk",
                "/data/storage/el1/bundle/libs/arm64",
            ])
            with env.vars(self).apply():
                self.run(executable, ignore_errors=False)
