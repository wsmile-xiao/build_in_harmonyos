#!/usr/bin/env python3
"""Conan test_package — 消费者视角验证 workflow HTTP 往返（R34 实质调用）。"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class WorkflowTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # 运行期 test_package 链接 libworkflow.so（conan 包 lib 目录）。
        # openssl 为 workflow 的传递依赖（CMakeDeps 生成 workflow-config.cmake
        # 的 find_dependency），运行时需其 lib 目录在搜索路径。
        env = Environment()
        for dep_name in ("workflow", "openssl"):
            dep = self.dependencies.get(dep_name)
            if dep is None or not getattr(dep, "package_folder", None):
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        # 工具链 libc++_shared.so（测试二进制 NEEDED libc++_shared）
        cc = str(self.conf.get("tools.build:compiler_executables", {}).get(
            "cpp", "")) if self.conf.get("tools.build:compiler_executables") else ""
        if cc:
            cc_real = os.path.realpath(cc)
            cand = os.path.join(
                os.path.dirname(os.path.dirname(cc_real)),
                "lib", "aarch64-linux-ohos",
            )
            if os.path.isfile(os.path.join(cand, "libc++_shared.so")):
                env.prepend_path("LD_LIBRARY_PATH", cand)
        env.vars(self, scope="build").save_script("test_workflow_env")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.build_folder, "test_package")
        # 运行期搜索路径由 generate() 的 build scope env 注入
        # （LD_LIBRARY_PATH：workflow/openssl lib + 工具链 libc++_shared.so）
        self.run(f'"{exe}"', env="conanbuild")
