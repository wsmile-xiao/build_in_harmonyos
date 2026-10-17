#!/usr/bin/env python3
"""Conan test_package for libheif-aom 1.23.0（消费者视角，R34：真实调用交付面 API）。

验证三件事：
  1. 链接：`find_package(libheif)` 找到本包交付的宿主（CMakeDeps，目标 libheif::libheif）；
  2. 运行：`LIBHEIF_PLUGIN_PATH` / `LD_LIBRARY_PATH` 由本包 `package_info()` 的
     `runenv_info` 经 VirtualRunEnv（`env="conanrun"`）带出；
  3. 功能：宿主 dlopen 交付的两个插件模块后
     `heif_have_decoder_for_format(heif_compression_AV1) == 1`、
     `heif_have_encoder_for_format(heif_compression_AV1) == 1`，
     并完成一次 AV1 编码→内存→解码的端到端往返（见 test_libheif_aom.c）。

CI 通过 `conan create` 自动执行本测试。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibheifAomTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # 共享设备口径：Conan 的 CMake.build() 默认按 os.cpu_count() 追加 `-j20`，
        # 这里在它之后追加显式 `-j<N>`（make 取**最后一个** -j），默认 2、可由
        # `-c tools.build:jobs=N` 覆盖——与主配方 `_jobs()` 同一口径。
        jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)
        cmake.build(build_tool_args=[f"-j{jobs}"])

    def test(self):
        # env="conanrun"：VirtualRunEnv 脚本（含本包 runenv_info 导出的
        # LIBHEIF_PLUGIN_PATH，以及 cpp_info.libdirs 的 LD_LIBRARY_PATH）。
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_libheif_aom"),
            env="conanrun",
        )
