#!/usr/bin/env python3
"""Conan test_package — spice 0.16.0 (consumer view)。

三个测试对打包产物做消费侧验证（逐用例 TEST PASS/FAIL + TEST SUMMARY）：

* ``test_spice_server_api`` — 链接 spice-server::spice-server 真实调用
  spice_server_new / set_port / set_name / set_ticket / destroy 的公开 API 契约；
* ``test_ohos_platform``    — 鸿蒙特有 #1（平台 ABI）：包内 libspice-server.so
  带 OHOS aarch64 / musl / libc++ 平台特征且 OHOS 加载器可 dlopen；
* ``test_ohos_runtime``     — 鸿蒙特有 #2（运行时闭包）：在 OHOS 加载器下解析
  libspice-server.so 的全部 DT_NEEDED 闭包，并通过 loader 路径真实调用 API。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class SpiceServerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: spice consumer tests skipped")
            return
        lib = os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                           "lib", "libspice-server.so")
        bindir = self.cpp.build.bindirs[0]
        self.run('"{}/test_spice_server_api"'.format(bindir), env="conanrun")
        self.run('"{}/test_ohos_platform" "{}"'.format(bindir, lib), env="conanrun")
        self.run('"{}/test_ohos_runtime" "{}"'.format(bindir, lib), env="conanrun")
