#!/usr/bin/env python3
"""Conan test_package for libheif-openh264 1.23.0（消费者视角，R34：真实调用交付面 API）。

验证四件事：
  1. 链接：`find_package(libheif)` 找到本包交付的宿主（CMakeDeps，目标 libheif::libheif）；
  2. 运行：`LIBHEIF_PLUGIN_PATH` / `LD_LIBRARY_PATH` 由本包 `package_info()` 的
     `runenv_info` 与依赖图的 libdirs 经 VirtualRunEnv（`env="conanrun"`）带出；
  3. 功能：宿主 dlopen 交付的插件模块 `libheif-openh264dec.so` 后
     `heif_have_decoder_for_format(heif_compression_AVC) == 1`；
  4. R40（多媒体类）：同一运行期链路上的 libopenh264 真实跑一次 H.264 编码→解码回环。

为什么 openh264 用显式路径而不是 `find_package(openh264)`：CMakeDeps 对**未被直接依赖
re-export 的传递依赖**只写 libdirs/bindirs，`includedirs`/`libs` 为空（实测：把
openh264 写成直接 `requires` 时非空，经 `libheif-openh264` 传递时为空）；而本测试要真跑
openh264 的编解码 API。这里从 `self.dependencies` 解析实际路径后作为 cache 变量下发，
口径与既有先例 `archives/o/openh264/2.6.0/test_package/conanfile.py`（从依赖取 include/libdir）
一致。被测包自己的交付面仍走标准 CMakeDeps（`find_package(libheif)`）。

CI 通过 `conan create` 自动执行本测试。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibheifOpenh264TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        dep = self.dependencies["openh264"]
        tc = CMakeToolchain(self)
        tc.cache_variables["OPENH264_INCLUDE_DIRS"] = ";".join(
            self._absolute(dep, dep.cpp_info.includedirs, "include"))
        tc.cache_variables["OPENH264_LIBDIR"] = self._absolute(
            dep, dep.cpp_info.libdirs, "lib")[0]
        tc.cache_variables["OPENH264_LIBNAME"] = (
            list(dep.cpp_info.libs) or ["openh264"])[0]
        tc.generate()

    def _absolute(self, dep, dirs, fallback):
        """把依赖声明的相对目录解析成包内绝对路径。"""
        result = []
        for rel in (list(dirs) or [fallback]):
            result.append(rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel))
        return result

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # env="conanrun"：VirtualRunEnv 脚本（含本包 runenv_info 导出的
        # LIBHEIF_PLUGIN_PATH，以及本包与依赖 libdirs 的 LD_LIBRARY_PATH）。
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_libheif_openh264"),
            env="conanrun",
        )
