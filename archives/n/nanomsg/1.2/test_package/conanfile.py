#!/usr/bin/env python3
"""Conan test_package — nanomsg 1.2 消费者级验证（L1）.

CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NanomsgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        # R34：实质执行被测包（消费者进程真实调用 nn_socket/nn_send/nn_recv
        # 完成 inproc+tcp 回环通信，非空壳打印）
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_nanomsg")
        self.run(f'"{cmd}"', env="conanrun")
