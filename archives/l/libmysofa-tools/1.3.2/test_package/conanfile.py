#!/usr/bin/env python3
"""Conan test_package for libmysofa-tools 1.3.2.

Builds and runs three consumer checks against the packaged libmysofa-tools:
  - test_libmysofa: open a real SOFA file (data/testfile.sofa), fetch an
    HRTF filter via mysofa_getfilter_float and verify finite outputs
  - ohos_special_test: HarmonyOS-specific checks (coordinate roundtrip,
    filter finite values, minphase/resample, multithreaded lookups)
  - ohos_tool_mysofa2json: NEW HarmonyOS consumer test for the -tools
    deliverable — runs the packaged mysofa2json executable against the
    decoded fixture and verifies it emits a non-empty SOFA JSON document
Both C binaries run via ctest inside test(); the L0d gate requires test()
to actually execute the built binaries (R34/PF3 - no empty shells).
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
import os


class LibmysofaToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def configure(self):
        # 与主配方一致：显式 Ninja 生成器（本机 OHOS 环境下 make 的 recipe
        # /bin/sh 派生链存在 exec 异常的环境回归，ninja 不受影响）。
        # 必须在 generators 属性实例化 CMakeToolchain 之前 define，
        # 故放 configure() 而非 generate()。
        self.conf.define("tools.cmake.cmaketoolchain:generator", "Ninja")

    def layout(self):
        cmake_layout(self)

    def _tool_bin(self):
        # 定位被测包 bin/ 下的 mysofa2json 绝对路径：ctest 经 make test
        # 间接执行、self.run 经 /system/bin/sh 执行，包 bin/ 均不在 PATH，
        # 必须全程使用绝对路径
        for dep in self.dependencies.values():
            if getattr(dep.ref, "name", "") == "libmysofa-tools":
                return os.path.join(dep.cpp_info.bindirs[0], "mysofa2json")
        raise ConanException("libmysofa-tools dependency not found in graph")

    def build(self):
        cmake = CMake(self)
        cmake.configure(cli_args=["-DMYSOFA2JSON=%s" % self._tool_bin()])
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # L0d gate: explicitly run the tested binaries (no empty shell).
        # 数据文件 data/testfile.sofa 由 CMake 在构建期从 base64 解码到
        # <build>/data/，二进制与 ctest 工作目录均在 bin_dir，直接运行
        # 须以 bin_dir 为 cwd（与 ctest WORKING_DIRECTORY 一致）
        bin_dir = os.path.abspath(self.cpp.build.bindirs[0])
        self.run(os.path.join(bin_dir, "test_libmysofa"), env="conanrun",
                 cwd=bin_dir)
        self.run(os.path.join(bin_dir, "ohos_special_test"), env="conanrun",
                 cwd=bin_dir)
        # 新增鸿蒙消费者用例（与 ctest 用例 ohos_tool_mysofa2json 同一断言，
        # 直接驱动打包出的 mysofa2json 工具，绝对路径调用）
        self.run("\"%s\" -c data/testfile.sofa > tool_out.json && "
                 "test -s tool_out.json && grep -q '\"M\"' tool_out.json"
                 % self._tool_bin(), env="conanrun", cwd=bin_dir)
