#!/usr/bin/env python3
"""Test package for captagent - build and run a real C test driver.

R34: the test must execute the packaged binary and verify it works.
test.c invokes `captagent -v` / `captagent -h` and asserts rc==0 plus
expected output markers (version string "6.4.4", usage "-f").
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class CaptagentTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # 构建输出隔离到 test_package/build-release/，避免污染源码目录
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            env = Environment()
            # 定位被测包 captagent 的 sbin 目录（主配方 runenv PATH 未传播到 test_package）
            for dep in self.dependencies.values():
                if dep.ref.name == "captagent" and dep.package_folder:
                    for sub in ("sbin", "bin"):
                        d = os.path.join(dep.package_folder, sub)
                        if os.path.isdir(d):
                            env.append_path("PATH", d)
                            self.output.info("PATH += " + d)
            # captagent 主程序 NEEDED libexpat.so，且各模块在运行期 dlopen
            # 依赖库（expat/json-c/libuv/libpcap 的 shared 产物）；手动收集所有
            # 依赖 lib 目录注入 LD_LIBRARY_PATH，确保运行时可加载
            lib_dirs = []
            for dep in self.dependencies.values():
                if not dep.package_folder:
                    continue
                lib = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib):
                    lib_dirs.append(lib)
            if lib_dirs:
                env.append_path("LD_LIBRARY_PATH", os.pathsep.join(lib_dirs))
                self.output.info("LD_LIBRARY_PATH += " + os.pathsep.join(lib_dirs))
            envvars = env.vars(self)
            with envvars.apply():
                # 运行 C 测试驱动：验证 captagent -v / -h 真实输出
                self.run("./captagent_test")
