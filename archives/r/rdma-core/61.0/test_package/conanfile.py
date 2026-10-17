#!/usr/bin/env python3
"""Conan test_package — L1 test + HarmonyOS 专项测试 + 消费者用例.

E298/E339: 测试二进制运行期需要被测包内动态库；通过 Environment
显式把被测包 lib 目录追加到 LD_LIBRARY_PATH 后执行三个测试。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class RdmaCoreTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def configure(self):
        # 与主配方一致，强制静态链接被测包，使测试二进制不依赖运行期共享库加载
        self.options["rdma-core"].shared = False

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        build_bin = os.path.join(self.cpp.build.bindirs[0]) \
            if self.cpp.build.bindirs else self.build_folder
        # 显式注入被测包 lib 目录，保证测试二进制运行时能加载包内动态库
        env = Environment()
        lib_dir = os.path.join(
            self.dependencies["rdma-core"].package_folder, "lib")
        env.append_path("LD_LIBRARY_PATH", lib_dir)
        envvars = env.vars(self)
        with envvars.apply():
            # L1 基础测试: 消费者视角调用 libibverbs + librdmacm 公共 API
            self.run(os.path.join(build_bin, "test_rdma-core"))
            # 鸿蒙专项测试: 验证 OHOS musl 适配点
            self.run(os.path.join(build_bin, "test_ohos_specific"))
            # 消费者用例: 模拟业务上层组件
            self.run(os.path.join(build_bin, "test_consumer"))