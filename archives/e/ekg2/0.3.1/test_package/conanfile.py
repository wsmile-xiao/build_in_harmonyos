#!/usr/bin/env python3
"""Test package for ekg2 - build and run a real C test driver.

R34: the test must execute the packaged binary and verify it works.
test.c invokes `ekg2 --help` and asserts rc==0 plus expected help markers.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.env import Environment, VirtualRunEnv


class Ekg2TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            env = Environment()
            # 定位被测包 ekg2 的 bin 目录（主配方 runenv PATH 未传播到 test_package）
            for dep in self.dependencies.values():
                if dep.ref.name == "ekg2" and dep.package_folder:
                    ekg2_bin = os.path.join(dep.package_folder, "bin")
                    if os.path.isdir(ekg2_bin):
                        env.append_path("PATH", ekg2_bin)
                        self.output.info("PATH += " + ekg2_bin)
            # 依赖库（如 gnutls）以 shared 产物存在但配方标 shared=False，
            # VirtualRunEnv 不会注入其 lib 路径；手动收集所有依赖 lib 目录
            # 并注入 LD_LIBRARY_PATH，确保 ekg2 运行时可加载 gnutls 等 .so
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
                # 运行 C 测试驱动：验证 ekg2 --help 输出帮助信息
                self.run("./ekg2_test")
