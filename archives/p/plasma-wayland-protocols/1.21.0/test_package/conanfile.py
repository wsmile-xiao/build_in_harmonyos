#!/usr/bin/env python3
"""Conan test_package for plasma-wayland-protocols — CMake consumer test.

Verifies the packaged PlasmaWaylandProtocols CMake package:
find_package(PlasmaWaylandProtocols 1.21 CONFIG) resolves and
PLASMA_WAYLAND_PROTOCOLS_DIR points at the installed XML set
(32 XMLs = 30 protocols + 2 renamed backward-compat files).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PlasmaWaylandProtocolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        pkg = self.dependencies["plasma-wayland-protocols"].package_folder
        # cmake_find_mode=none -> 上游 Config 包不进 CMAKE_PREFIX_PATH,
        # 消费者侧显式加目录(与 kwayland 6.7.2 配方同款消费方式)。
        tc.variables["PWP_SHARE_CMAKE"] = os.path.join(
            pkg, "share", "cmake", "PlasmaWaylandProtocols")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        pkg = self.dependencies["plasma-wayland-protocols"].package_folder

        # 断言 1-2: Config 包两个文件存在
        cfg_dir = os.path.join(pkg, "share", "cmake", "PlasmaWaylandProtocols")
        for f in ("PlasmaWaylandProtocolsConfig.cmake",
                  "PlasmaWaylandProtocolsConfigVersion.cmake"):
            if not os.path.isfile(os.path.join(cfg_dir, f)):
                raise Exception(f"{f} not found in {cfg_dir}")
        self.output.info(f"config package files found in {cfg_dir}")

        # 断言 3: CMake 消费者可执行文件(fconfigure 阶段完成
        # find_package(CONFIG) + XML 清单校验,可执行文件仅占位)
        self.run(os.path.join(self.build_folder, "pwp_consumer_test"),
                 env="conanrun")
        self.output.info("CMake consumer find_package check PASS")

        # 断言 4: shell 脚本深检 XML 清单与改名兼容文件
        script = os.path.join(self.source_folder, "src",
                              "test_plasma-wayland-protocols.sh")
        if os.path.isfile(script):
            self.run(f'bash "{script}" "{pkg}"', env="conanrun")

        self.output.info("plasma-wayland-protocols test_package PASS")
