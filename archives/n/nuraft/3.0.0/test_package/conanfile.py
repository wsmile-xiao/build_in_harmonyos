#!/usr/bin/env python3
"""Conan test_package for nuraft — 3-node in-memory Raft cluster smoke test.

消费者视角验证：真实调用 nuraft 公共 API（raft_launcher / raft_server /
append_entries / add_srv / get_committed_log_idx），在单进程内起 3 节点
内存状态机集群（asio 回环地址），验证 leader 选举 + 日志复制 + commit index 前进。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NuRaftTestConan(ConanFile):
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
        # Run the smoke test binary directly (L0d/R34 requires self.run())
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_nuraft")
        self.run(test_binary, env="conanrun")