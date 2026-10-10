#!/usr/bin/env python3
"""Conan test_package for libfuse 3.16.1 (fuse3 on OpenHarmony aarch64).

R34: the test binary really links against libfuse3 and calls its public API
(version handshake, option parser, FUSE object lifecycle, low-level session
including the multi-threaded loop).  Mounting a filesystem is not attempted
because OHOS user space does not expose /dev/fuse.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibfuseTestConan(ConanFile):
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
        # R34: run the consumer program, which must link against the packaged
        # libfuse3 and drive the pthread_cancel-free cleanup thread and the
        # multi-threaded session loop.
        bin_path = os.path.join(self.cpp.build.bindir, "test_libfuse")
        self.run(f'"{bin_path}"', env="conanrun")
        # 鸿蒙特有：完整端到端消费者用例（内存文件系统工作流 + pthread_cancel
        # 替代路径内容校验）
        consumer_path = os.path.join(self.cpp.build.bindir, "test_fs_consumer")
        self.run(f'"{consumer_path}"', env="conanrun")
