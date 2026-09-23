#!/usr/bin/env python3
"""Conan test_package for libheif-jpeg 1.23.0（消费者视角，R34：真实调用交付面 API）。

验证四件事：
  1. 链接：`find_package(libheif)` 找到本包交付的宿主（CMakeDeps，目标 libheif::libheif）；
  2. 运行：`LIBHEIF_PLUGIN_PATH` / `LD_LIBRARY_PATH` 由本包 `package_info()` 的
     `runenv_info` 经 VirtualRunEnv（`env="conanrun"`）带出；
  3. 功能：宿主 dlopen 交付的插件模块 `libheif-jpegdec.so` / `libheif-jpegenc.so` 后
     `heif_have_decoder_for_format(heif_compression_JPEG) == 1` 且
     `heif_have_encoder_for_format(heif_compression_JPEG) == 1`；
  4. 端到端：JPEG 编码 → 写 .jpg → JPEG 解码 → 尺寸与像素一致（有损容差 ±10）。

CI 通过 `conan create` 自动执行本测试。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibheifJpegTestConan(ConanFile):
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
        # 往返用到的 .jpg 写在构建目录（设备 /tmp 只读，不能写 /tmp）。
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_libheif_jpeg"),
            env="conanrun",
        )
