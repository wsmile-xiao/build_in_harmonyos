#!/usr/bin/env python3
"""Conan test_package — openexr 3.3.4 消费者视角验证。

验证点：
1. OpenEXR::OpenEXR（C++ API，含 imath 传递依赖）
2. OpenEXR::OpenEXRCore（C API，含 libdeflate 链路）
test() 显式 self.run 两个测试二进制（R34：禁止空壳测试）。
设备本地（os=OHOS）可直接执行；CI 远端跑 conan create 时由
CMake test 驱动 ctest，二者等价执行同一组断言。

注意：本仓库 imath/3.2.2 配方的组件 includedirs 只声明 include/，
缺少上游 ImathConfig 组件的 include/Imath 目录（上游 ImathTargets
的 Imath::ImathConfig 同时暴露 include 与 include/Imath）。OpenEXR
公开头以 <ImathConfig.h>/<ImathBox.h> 引用 Imath 头，消费侧在此
补齐 imath 的 includedirs（与主配方 generate() 同款修法）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class OpenexrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # imath 组件 includedirs 补齐 include/Imath（同主配方 generate()）
        imath_info = self.dependencies["imath"].cpp_info
        for info in [imath_info] + list(imath_info.components.values()):
            dirs = list(info.includedirs)
            if not any(d.endswith("include/Imath") or d.endswith("include\\Imath")
                       for d in dirs):
                for d in dirs:
                    if d.endswith("include"):
                        dirs.append(os.path.join(d, "Imath"))
                        break
                info.includedirs = dirs

        deps = CMakeDeps(self)
        deps.set_property("libdeflate", "cmake_target_name",
                          "libdeflate::libdeflate_shared")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: test() 必须实质执行被测包——两个测试二进制均 self.run
        #（CMakeLists 不含 add_test/enable_testing，无 ctest 目标）
        bin_dir = self.cpp.build.bindirs[0]

        # OHOS consumers link against the platform libc++_shared.so which
        # lives in /system/lib64.  Pin the loader path explicitly so the
        # test binary stays runnable even when the ambient
        # LD_LIBRARY_PATH is malformed on the host shell.
        # （同 archives/d/date/3.0.5 先例；conanrun 会叠加依赖包 libdirs）
        test_env = Environment()
        test_env.define("LD_LIBRARY_PATH", "/system/lib64")

        failed = False
        with test_env.vars(self).apply():
            for exe in ("test_openexr", "test_core"):
                path = os.path.join(bin_dir, exe)
                if os.path.exists(path):
                    self.run(path, env="conanrun")
                else:
                    self.output.error(f"missing test binary: {path}")
                    failed = True
        if failed:
            raise Exception("test binaries missing")
