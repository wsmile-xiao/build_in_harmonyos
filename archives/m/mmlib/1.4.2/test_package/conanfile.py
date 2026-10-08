#!/usr/bin/env python3
"""Conan test_package — mmlib 1.4.2 (consumer view)。

三个测试对打包产物做消费侧验证（逐用例 TEST PASS/FAIL + TEST SUMMARY）：

* ``test_mmlib_api``      — 链接 mmlib::mmlib 真实调用公开 API 契约
  （aligned_alloc / gettime+sleep / thr_mutex / env / unlink+last-error）；
* ``test_ohos_platform``  — 鸿蒙特有：包内 libmmlib.so 平台 ABI 实测
  （ELF64/EM_AARCH64/PT_DYNAMIC）+ OHOS 加载器 dlopen(RTLD_NOW) 与
  dlsym 契约符号，并经 loader 路径真实调用 mm_gettime；
* ``test_mmlib_e2e``      — 消费者最小应用管线（E2E）：配置流 +
  mm_ipc_connected_pair/fork 跨进程数据管线（对齐载荷双向收发校准校验和）
  + mmap/MM_THR_PSHARED 跨进程互斥计数。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class MmlibTestConan(ConanFile):
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
            self.output.info("cross-building: mmlib consumer tests skipped")
            return
        lib = os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                           "lib", "libmmlib.so")
        bindir = self.cpp.build.bindirs[0]
        self.run('"{}/test_mmlib_api"'.format(bindir), env="conanrun")
        self.run('"{}/test_ohos_platform" "{}"'.format(bindir, lib), env="conanrun")
        self.run('"{}/test_mmlib_e2e"'.format(bindir), env="conanrun")
