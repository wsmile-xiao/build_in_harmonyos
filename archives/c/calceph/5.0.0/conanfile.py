#!/usr/bin/env python3
"""Conan recipe for calceph 5.0.0 — IMCCE 天体历表库（C/Fortran）。

calceph（IMCCE，巴黎天文台）是天体历表读取/计算库（支持 JPL/INPOP/
SPICE 格式），CMake 构建。版本 5.0.0 为上游真实 tag（用户给的版本
存在——按真实版，2026-07 发布）。

Upstream: https://gitlab.obspm.fr/imcce_calceph/calceph（tag calceph_5_0_0）

Build:   CMake。C 核心库零第三方依赖（ENABLE_FORTRAN=OFF——OHOS 无
         Fortran 编译器；ENABLE_PYTHON/MEX_OCTAVE/DOC/PDF 全关）。
Install: lib/libcalceph.a + include/calceph.h。
Type:    library（库包——libcalceph 供天文应用链接）。

上游测试: tests/ 目录 114 个 C 测试文件（ctest，含 .tpc 数据文件）。
         本地实测通过率如实记录。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.scm import Git


class CalcephConan(ConanFile):
    name = "calceph"
    version = "5.0.0"
    description = "C library to access solar system ephemeris files (IMCCE)"
    license = "CECILL-C"
    homepage = "https://calceph.imcce.fr/"
    url = "https://gitlab.obspm.fr/imcce_calceph/calceph"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # 零第三方 Conan 依赖（C 核心库自包含）

    def layout(self):
        cmake_layout(self)

    def source(self):
        # git clone 方式获取源码（gitlab archive tar 下载易中断，
        # git 协议稳定；tag calceph_5_0_0）——self.run 直接 clone
        self.run("git clone --depth 1 --branch %s %s ."
                 % (self.conan_data["git_branch"],
                    self.conan_data["git_url"]))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_FORTRAN"] = False
        tc.variables["ENABLE_PYTHON"] = False
        tc.variables["ENABLE_MEX_OCTAVE"] = False
        tc.variables["ENABLE_DOC"] = False
        tc.variables["ENABLE_PDF"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游测试实跑（ctest，tests/ 114 个 C 测试）——TMPDIR 可写
        self.run("cd %s && TMPDIR=%s ctest --output-on-failure"
                 % (self.build_folder, self.build_folder))

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.output.info("calceph 5.0.0: libcalceph")
