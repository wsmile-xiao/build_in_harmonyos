#!/usr/bin/env python3
"""Conan test_package for boost-defaults 1.90.0.2 — metapackage consumer test.

boost-defaults 是 requirements-only 元包：自身无源码/库/头文件，消费语义 =
"通过 boost-defaults 拿到默认版本 Boost（1.90）的全部开发资源"。

本测试从消费者视角验证元包语义（R34 实质依赖被测包）：
  1. 通过 boost-defaults 的 requires 传播，<boost/version.hpp> 等 Boost
     头文件可用（元包核心价值：include 路径传播自 boost/1.90.0）；
  2. 头文件报出的 BOOST_LIB_VERSION / BOOST_VERSION 与默认版本 1.90 一致；
  3. CMake 组件目标可用：find_package(Boost) + Boost::boost 头文件目标 +
     boost-defaults::boost_defaults 元组件目标均可解析并链接；
  4. 编译并真实运行一个多组件消费者（smart_ptr 头文件 + Boost.Test
     编译库），3 个测试用例共 8 处断言全部通过。

运行时环境：OHOS 加载器需能定位 libc++_shared.so（系统库，位于
/system/lib64），用 Environment 注入（先例 archives/b/bitcoin/31.1.1
test_package 同款模式——依赖未声明 runenv_info 时手动注入）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BoostDefaultsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    # OHOS 系统库目录（libc++_shared.so 由系统提供）
    _OHOS_SYSTEM_LIB_DIRS = ("/system/lib64", "/system/lib")

    def requirements(self):
        # 只依赖被测元包——boost/1.90.0 必须经由 boost-defaults 传播进来
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Skipping boost-defaults runtime test while cross-building"
            )
            return

        # OHOS: 测试二进制动态依赖系统 libc++_shared.so；conanrun 环境不含
        # 系统库路径时在命令前缀注入（先例 archives/b/barvinok/0.41.9
        # test_package 同款模式——boost/1.90.0 未声明 runenv_info）
        env_prefix = ""
        if str(self.settings.os) == "OHOS":
            dirs = [d for d in self._OHOS_SYSTEM_LIB_DIRS if os.path.isdir(d)]
            if dirs:
                env_prefix = (
                    "LD_LIBRARY_PATH=\"" + ":".join(dirs)
                    + ":$LD_LIBRARY_PATH\" "
                )

        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        test_binary = os.path.join(
            self.cpp.build.bindirs[0], f"test_boost_defaults{suffix}"
        )
        self.run(f'{env_prefix}"{test_binary}"',
                 cwd=self.build_folder, env="conanrun")
