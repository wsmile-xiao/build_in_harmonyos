#!/usr/bin/env python3
"""Conan test_package for kwayland 6.7.2 — CMake 消费者 + E2E 往返验证.

上游 kwayland 6.7.2 未注册 ctest 测试（tests/CMakeLists.txt 只构建
12 个可执行文件，运行依赖的 testserver 已移出本仓库），运行时验证由
本 test_package 承担：client_roundtrip 在进程内起迷你 Wayland 合成器
（socketpair + wl_client_create + wl_compositor v4 global），
KWaylandClient 经 ConnectionThread::setSocketFd 接入，Registry 收到
interfacesAnnounced 后 createCompositor → createSurface → commit →
flush，断言服务端 create_surface 计数 == 1。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KwaylandTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # KWaylandConfig.cmake find_dependency(Qt6Gui) + KWaylandClient
        # 的 DT_NEEDED（Qt6Gui/Qt6Concurrent/Qt6WaylandClient/
        # libwayland-client）都要在同一 host 图里；libEGL 属 OHOS 系统
        # 库（/system/lib64/libEGL.so），无需制品仓依赖（mesa 的
        # expat/2.8.2.1.1 与 qtbase 链的 expat/2.8.2 图冲突）
        self.requires("qtbase/6.11.1.2")
        self.requires("qtwayland/6.11.1")
        self.requires("wayland/1.22.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        kw = self.dependencies["kwayland"].package_folder
        # qtbase/kwayland 都是 cmake_find_mode=none：CMakeDeps 不生成也不
        # 加 CMAKE_PREFIX_PATH，消费者显式 prepend（kwayland 配方同款）
        tc.variables["QT6_CMAKE_DIR"] = os.path.join(qtbase, "lib", "cmake")
        tc.variables["KWAYLAND_CMAKE_DIR"] = os.path.join(kw, "lib", "cmake")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 运行时依赖解析：test_package 自动带 VirtualRunEnv，conanrun 环境
        # 文件里 host 图全部依赖（kwayland/qtbase/qtwayland/wayland/... 共
        # 16 个 lib 目录）的 LD_LIBRARY_PATH 已就位；ConanFile.run 的 env
        # 参数只接受环境文件名（字符串或列表），传 Environment 对象会挂
        # AttributeError（conan 2.29 ConanFile.run 签名，第七轮 G2 实录）
        exe = os.path.join(self.build_folder, "client_roundtrip")
        # QCoreApplication 不需要平台插件；offscreen 只作兜底（KWayland
        # 内部万一走 QGuiApplication 路径），内联在命令行里
        self.run('QT_QPA_PLATFORM=offscreen "%s"' % exe, env="conanrun")
        self.output.info("kwayland 6.7.2 E2E roundtrip PASS")
