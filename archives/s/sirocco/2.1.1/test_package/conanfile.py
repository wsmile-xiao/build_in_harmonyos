#!/usr/bin/env python3
"""Conan test_package — sirocco 2.1.1 (L1 consumer test)

Verifies the packaged libsirocco can be found/linked, and that the real
certified root-continuation API (homotopyPath / _comps / _mp / _mp_comps)
runs on the HarmonyOS device.  One add_test() in CMakeLists.txt, so
discovered/passedCount == 1.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SiroccoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # sirocco.h 直接 #include <mpfr.h>，且 conanfile 的 cpp_info.requires
        # 引用 gmp::gmp / mpfr::mpfr，因此这里显式 require 让 CMakeDeps 生成
        # 对应 .pc/.cmake 目标（同 flint/arb test_package 惯例）。
        # 版本与主包 requirements 对齐：gmp/6.3.0.1、mpfr/4.2.2.1 为本仓专属
        # 补丁版本，强制 ohpcd 解析、避免 conancenter 裸版本带 m4 源码构建失败。
        # 与主包一致：gmp/mpfr 用【真实直接依赖】（勿 override=True，否则
        # self.dependencies 无对应节点）；gmp 用 force=True 压过 mpfr 钉的 6.3.0。
        self.requires("mpfr/4.2.2.1")
        self.requires("gmp/6.3.0.1", force=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_sirocco")
        self.run(bin_path, env="conanrun")
        # Machine-readable result for the HMBS gate; one add_test() in
        # CMakeLists.txt, so discovered/passedCount == 1.
        print(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
                "executed": True,
                "passed": True,
                "command": bin_path,
                "discovered": 1,
                "passedCount": 1,
            })
        )
