#!/usr/bin/env python3
"""test_package — getdns 1.7.3 OHOS 冒烟测试。

真实 OHOS 验证（非空壳，R34/PF3）：
- getdns_smoke.c 在 OHOS 工具链下编译（__OHOS__ 宏探测打印平台名）
- 调用 libgetdns 核心 API：getdns_context_create/destroy、
  getdns_dict_set/get_bindata、getdns_dict_get_names、
  getdns_pretty_print_dict、getdns_get_version —— 实链验证交叉编译
  产物符号可用
- self.run() 实际执行编译出的二进制（CI worker = OHOS PC 本机）
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import can_run
from conan.tools.env import Environment


class GetdnsTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        # explicit test：conan create 注入 tested_reference_str
        self.requires(self.tested_reference_str)
    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            binpath = os.path.join(self.cpp.build.bindirs[0], "getdns_smoke")
            self.run(f'"{binpath}"', env="conanrun")
