#!/usr/bin/env python3
"""Conan test_package for libheif-svtenc 1.23.0（消费者视角，R34：真实调用交付面 API）。

验证三件事：
  1. 链接：`find_package(libheif)` 找到本包交付的宿主（CMakeDeps，目标 libheif::libheif）；
  2. 运行：`LIBHEIF_PLUGIN_PATH` / `LD_LIBRARY_PATH` 由本包 `package_info()` 的
     `runenv_info`（以及 `libdirs`）经 VirtualRunEnv（`env="conanrun"`）带出——
     前者让宿主找到交付的插件模块，后者让插件找到同包的 libSvtAv1Enc.so；
  3. 功能：宿主 dlopen 交付的插件后 `heif_have_encoder_for_format(AV1)==1`，
     并真实编码一张 128x128 AVIF（进入 SVT-AV1 编码器）。

CI 通过 `conan create` 自动执行本测试。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibheifSvtencTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # env="conanrun"：VirtualRunEnv 脚本（含本包 runenv_info 导出的
        # LIBHEIF_PLUGIN_PATH，以及 cpp_info.libdirs 的 LD_LIBRARY_PATH）。
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_libheif_svtenc"),
            env="conanrun",
        )
